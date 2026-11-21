// O08 Registrar a conclusão junto da análise que a sustenta (cena única para os três MoLIC).
// O tipo define os campos: validação (P01), experimento (P02) e recomendação (P03).
// O08.1 Informar a conclusão · O08.2 Conferir a conclusão ("confirmar" ou "corrigir").
import { api, enc, ErroApi } from '../api.js';
import { h, limpar, cabecalho, mensagem, termo, rotuloComTermo, dialogo, falhaDaApi, erroCampo, anunciar, formato, exigir } from '../ui.js';
import { imagensComResultado, rotuloImagem, textoAvaliacao } from './comum.js';
import { tabelaDesempenho } from './desempenho.js';

const TITULOS = {
  'validação': 'Registrar a conclusão da validação',
  experimento: 'Registrar a conclusão do experimento',
  'recomendação': 'Registrar a recomendação',
};

export async function renderNova(main, _p, consulta, contexto) {
  const tipo = consulta.get('tipo');
  if (!TITULOS[tipo]) throw new Error('Tipo de conclusão desconhecido.');

  const configuracoesIds = (consulta.get('configuracoes') || '').split(',').filter(Boolean);
  const dados = await carregarAnalise(tipo, consulta.get('sessao'), configuracoesIds, consulta.get('ciclo'), consulta.get('comparar_mesmo_assim') === '1');
  return formulario(main, { tipo, ...dados, contexto });
}

export async function renderCorrigir(main, { id }, _consulta, contexto) {
  const conclusao = await api.get(`/api/conclusoes/${enc(id)}`);
  const ids = conclusao.analise?.configuracoes?.map((c) => c.id) || [];
  const dados = await carregarAnalise(conclusao.tipo, conclusao.sessao, ids, conclusao.ciclo, true, conclusao.analise);
  return formulario(main, { tipo: conclusao.tipo, ...dados, contexto, existente: conclusao });
}

async function carregarAnalise(tipo, sessaoId, configuracoesIds, ciclo, compararMesmoAssim, analiseSalva) {
  const [configuracoes, ciclos] = await Promise.all([api.get('/api/configuracoes'), api.get('/api/ciclos')]);
  const sessao = sessaoId ? await api.get(`/api/sessoes/${enc(sessaoId)}`).catch(() => null) : null;
  if (sessao) sessao.imagens = imagensComResultado(sessao);

  let analise = analiseSalva || null;
  if (!analise && tipo !== 'validação' && configuracoesIds.length) {
    analise = await api.post('/api/desempenho', { configuracoes: configuracoesIds, ciclo: ciclo || null, comparar_mesmo_assim: compararMesmoAssim })
      .catch(() => api.post('/api/desempenho', { configuracoes: configuracoesIds, comparar_mesmo_assim: true }));
  }
  return { configuracoes, ciclos, sessao, analise, ciclo: ciclo || sessao?.ciclo || '' };
}

function formulario(main, { tipo, configuracoes, ciclos, sessao, analise, ciclo, contexto, existente }) {
  const campos = existente?.campos || {};
  const nomes = Object.fromEntries(configuracoes.map((c) => [c.id, c.nome]));

  limpar(main, cabecalho(existente ? `Corrigir: ${TITULOS[tipo].toLowerCase().replace('registrar a ', '')}` : TITULOS[tipo],
    'A conclusão é sua: o sistema registra o que você informar junto da análise que a sustenta.'));

  if (tipo === 'validação' && !sessao) {
    main.append(mensagem('falha', h('p', {}, 'A validação precisa partir de uma sessão de segmentação.')));
    return null;
  }

  const seletorConfiguracao = (nome, rotulo, ids, valor, obrigatoria) => h('fieldset', { 'data-campo': 'configuracao' },
    h('legend', {}, rotulo),
    ids.map((cid) => h('label', { class: 'opcao' }, h('input', { type: 'radio', name: nome, value: cid, checked: valor === cid }), nomes[cid] || cid)),
    obrigatoria ? null : h('label', { class: 'opcao' }, h('input', { type: 'radio', name: nome, value: 'nenhuma', checked: !valor || valor === 'nenhuma' }), 'Nenhuma'));

  const texto = (nome, rotulo, valor, ajuda, obrigatorio = false) => h('div', { class: 'campo', 'data-campo': nome },
    h('label', { for: `campo-${nome}` }, rotulo, obrigatorio ? '' : h('span', { class: 'suave' }, ' (opcional)')),
    ajuda ? h('span', { class: 'ajuda' }, ajuda) : null,
    h('textarea', { id: `campo-${nome}`, name: nome }, valor || ''));

  const partes = [];
  let idsAnalise = analise?.configuracoes?.map((c) => c.id) || [];

  if (tipo === 'validação') {
    idsAnalise = Object.keys(sessao.execucoes).filter((cid) => (sessao.execucoes[cid].concluidas || []).length);
    const duvidosas = sessao.imagens.filter((i) => sessao.avaliacoes[i.nome]?.avaliacao === 'duvidosa');
    const captura = new Set(campos.imagens_problema_captura
      || sessao.imagens.filter((i) => sessao.avaliacoes[i.nome]?.origem_problema === 'imagem (captura)').map((i) => i.nome));
    const inconclusivas = new Set(campos.imagens_inconclusivas || []);
    const caixa = (nome, imagem, marcado) => h('label', { class: 'opcao' },
      h('input', { type: 'checkbox', name: nome, value: imagem.nome, checked: marcado }),
      h('span', {}, rotuloImagem(imagem), h('span', { class: 'pequeno suave' }, ` · ${textoAvaliacao(sessao.avaliacoes[imagem.nome])}`)));

    partes.push(
      h('p', {}, h('strong', {}, 'Ciclo de testes: '), sessao.ciclo, ` · ${sessao.imagens.length} imagens`),
      seletorConfiguracao('configuracao_indicada', 'Qual configuração foi mais adequada?', idsAnalise, campos.configuracao_indicada, false),
      h('fieldset', {}, h('legend', {}, 'Quais imagens ficaram inconclusivas?'),
        duvidosas.length ? duvidosas.map((i) => caixa('imagens_inconclusivas', i, inconclusivas.has(i.nome)))
          : h('p', { class: 'suave pequeno' }, 'Nenhuma imagem está marcada como duvidosa.')),
      h('fieldset', {}, h('legend', {}, 'Em quais houve problema na imagem (captura)?'),
        duvidosas.length ? duvidosas.map((i) => caixa('imagens_problema_captura', i, captura.has(i.nome)))
          : h('p', { class: 'suave pequeno' }, 'Nenhuma imagem está marcada como duvidosa.')));
  } else {
    if (analise) {
      partes.push(h('div', { class: 'cartao', style: 'box-shadow:none' },
        h('h2', {}, 'Comparação que sustenta a conclusão'),
        tabelaDesempenho(analise)));
    } else {
      partes.push(mensagem('alerta', h('p', {}, 'Esta conclusão não tem uma comparação de desempenho associada.'),
        h('a', { href: '#/desempenho' }, 'Comparar o desempenho antes')));
    }

    if (tipo === 'experimento') {
      partes.push(
        texto('conclusao', 'Conclusão', campos.conclusao, 'Ex.: inconclusivo nas métricas; melhora visual nas sombras largas.', true),
        seletorConfiguracao('configuracao_candidata', 'Configuração candidata', idsAnalise, campos.configuracao_candidata, false),
        texto('ressalva', 'Ressalva', campos.ressalva),
        texto('proximo_experimento', 'Próximo experimento', campos.proximo_experimento));
    } else {
      const campoCiclo = h('input', { type: 'text', id: 'campo-ciclo', name: 'ciclo', value: existente?.ciclo || ciclo, list: 'ciclos-conclusao', autocomplete: 'off' });
      partes.push(
        h('div', { class: 'campo', 'data-campo': 'ciclo' }, rotuloComTermo('campo-ciclo', 'Ciclo de testes', 'ciclo_de_testes'), campoCiclo,
          h('datalist', { id: 'ciclos-conclusao' }, ciclos.map((c) => h('option', { value: c.ciclo })))),
        seletorConfiguracao('configuracao_indicada', 'Qual configuração você recomenda?', idsAnalise, campos.configuracao_indicada, true),
        texto('ressalva', 'Ressalva', campos.ressalva, 'Ex.: a diferença é pequena e o desempenho nos trechos de sombra não foi conferido.'));
    }
  }

  const botao = h('button', { type: 'submit', class: 'botao' }, existente ? 'Registrar a correção' : 'Registrar');
  const form = h('form', { class: 'cartao', novalidate: true }, partes, h('div', { class: 'linha' }, botao));
  main.append(form);

  // Campos obrigatórios conforme o tipo de conclusão (mesmo comportamento das outras telas)
  const valorDe = (nome) => (form.querySelector(`[name="${nome}"]`)?.value || '').trim();
  const regras = tipo === 'experimento'
    ? [{ campo: 'conclusao', valido: () => valorDe('conclusao').length > 0, mensagem: 'escreva a conclusão do experimento.' }]
    : tipo === 'recomendação'
      ? [
        { campo: 'ciclo', valido: () => valorDe('ciclo').length > 0, mensagem: 'informe o ciclo de testes.' },
        { campo: 'configuracao', valido: () => Boolean(form.querySelector('input[name="configuracao_indicada"]:checked')), mensagem: 'escolha a configuração que você recomenda.' },
      ]
      : [];
  const obrigatorios = exigir(form, botao, regras);

  form.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    if (!obrigatorios.atualizar()) return;
    erroCampo(form, null);
    const dadosForm = new FormData(form);
    const corpo = {
      tipo,
      sessao: sessao?.id || null,
      ciclo: dadosForm.get('ciclo') ?? (sessao?.ciclo || ciclo || null),
      analise: tipo === 'validação' ? null : analise,
      configuracao_indicada: dadosForm.get('configuracao_indicada'),
      configuracao_candidata: dadosForm.get('configuracao_candidata'),
      imagens_inconclusivas: dadosForm.getAll('imagens_inconclusivas'),
      imagens_problema_captura: dadosForm.getAll('imagens_problema_captura'),
      conclusao: dadosForm.get('conclusao'),
      ressalva: dadosForm.get('ressalva'),
      proximo_experimento: dadosForm.get('proximo_experimento'),
    };

    const enviar = (extra = {}) => (existente
      ? api.put(`/api/conclusoes/${enc(existente.id)}`, { ...corpo, ...extra })
      : api.post('/api/conclusoes', { ...corpo, ...extra }));

    botao.disabled = true;
    try {
      let conclusao;
      try {
        conclusao = await enviar();
      } catch (erro) {
        // Alerta: imagens sem avaliação (só na validação)
        if (erro instanceof ErroApi && erro.dados?.ruptura === 'imagens_sem_avaliacao') {
          const quantidade = erro.dados.quantidade;
          const escolha = await dialogo({
            tipo: 'alerta', titulo: 'Imagens sem avaliação',
            corpo: h('p', {}, `${quantidade === 1 ? 'Uma imagem ainda não tem' : `${quantidade} imagens ainda não têm`} avaliação. Quer concluir assim mesmo ou avaliá-las antes?`),
            acoes: [{ rotulo: 'Avaliá-las antes', valor: 'avaliar', primaria: true }, { rotulo: 'Concluir assim mesmo', valor: 'concluir' }],
          });
          if (escolha === 'avaliar') {
            contexto.navegar(`#/sessao/${enc(sessao.id)}/imagem?nome=${enc(erro.dados.primeira)}`);
            return;
          }
          if (escolha !== 'concluir') return;
          conclusao = await enviar({ concluir_assim_mesmo: true });
        } else {
          throw erro;
        }
      }
      anunciar(`${conclusao.tipo === 'recomendação' ? 'Recomendação registrada' : 'Conclusão registrada'}.`);
      contexto.navegar(`#/conclusao/${enc(conclusao.id)}`);
    } catch (erro) {
      if (erro instanceof ErroApi && erro.tipo === 'PA') erroCampo(form, erro);
      else await falhaDaApi(erro, 'Não foi possível registrar');
    } finally {
      obrigatorios.atualizar();
    }
  });
  return null;
}

export function resumoConclusao(conclusao, sessao) {
  const c = conclusao.campos;
  const imagem = (nome) => {
    const encontrada = sessao?.imagens.find((i) => i.nome === nome);
    return encontrada ? rotuloImagem(encontrada) : nome;
  };
  const lista = (nomesImagens) => (nomesImagens?.length ? nomesImagens.map(imagem).join(', ') : 'nenhuma');
  const itens = [['Tipo de conclusão', conclusao.tipo], ['Ciclo de testes', conclusao.ciclo || '—']];

  if (conclusao.tipo === 'validação') {
    itens.push(['Configuração mais adequada', c.configuracao_indicada_nome], ['Imagens inconclusivas', lista(c.imagens_inconclusivas)],
      ['Problema na imagem (captura)', lista(c.imagens_problema_captura)]);
  } else if (conclusao.tipo === 'experimento') {
    itens.push(['Conclusão', c.conclusao], ['Configuração candidata', c.configuracao_candidata_nome],
      ['Ressalva', c.ressalva || '—'], ['Próximo experimento', c.proximo_experimento || '—']);
  } else {
    itens.push(['Configuração indicada', c.configuracao_indicada_nome], ['Ressalva', c.ressalva || '—']);
  }
  itens.push(['Registrada em', formato.data(conclusao.atualizada_em)]);

  return h('dl', { class: 'resumo' }, itens.flatMap(([rotulo, valor]) => [h('dt', {}, rotulo), h('dd', {}, valor)]));
}

export async function renderConferir(main, { id }, _consulta, contexto) {
  const conclusao = await api.get(`/api/conclusoes/${enc(id)}`);
  const sessao = conclusao.sessao ? await api.get(`/api/sessoes/${enc(conclusao.sessao)}`).catch(() => null) : null;
  const titulo = conclusao.tipo === 'recomendação' ? 'Recomendação registrada' : 'Conclusão registrada';

  const destino = conclusao.tipo === 'validação' && sessao ? `#/sessao/${enc(sessao.id)}/imagem`
    : conclusao.tipo === 'recomendação' ? `#/apresentar?ciclo=${enc(conclusao.ciclo || '')}` : '#/desempenho';

  limpar(main, cabecalho('Conferir a conclusão', 'Confira o que foi registrado antes de sair.'),
    mensagem('ok', h('p', {}, h('strong', {}, `${titulo} `),
      conclusao.tipo === 'recomendação' ? `para o ciclo de testes "${conclusao.ciclo}".` : sessao ? 'para as imagens deste teste.' : 'junto da comparação.')),
    h('div', { class: 'cartao' }, resumoConclusao(conclusao, sessao),
      conclusao.analise ? h('div', { style: 'margin-top:1rem' }, h('h2', {}, 'Comparação que sustenta a conclusão'), tabelaDesempenho(conclusao.analise)) : null),
    h('div', { class: 'linha' },
      h('button', { type: 'button', class: 'botao', onclick: () => { anunciar('Conclusão confirmada.'); contexto.navegar(destino); } }, 'Confirmar'),
      h('a', { class: 'botao botao-secundario', href: `#/conclusao/${enc(id)}/corrigir` }, 'Corrigir')));
  return null;
}
