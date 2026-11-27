// M03, conversa 3 (preparar os dados de treino e de teste, O11), aberta pelo menu "Datasets":
// O11.1 Conferir os datasets · O11.2 Montar o dataset (alerta "Confirmar a remontagem") ·
// O11.3 Avaliar as configurações no conjunto de teste (uma de cada vez; ruptura "falha na avaliação").
// raw/ nunca é apagado: remontar não exige baixar de novo.
import { api, enc } from '../api.js';
import {
  h, limpar, cabecalho, mensagem, estado, progresso, dialogo, falhaDaApi, anunciar, formato, conjuntoTexto, exigir,
} from '../ui.js';

export async function render(main, _p, _c, contexto) {
  let dados = await api.get('/api/datasets');
  // Avaliações pedidas nesta visita: ao fim de todas, "Avaliação concluída"
  const pedidas = new Set();
  let montagemPedida = false;

  const corpo = h('div', {});
  limpar(main, cabecalho('Datasets', 'Prepare os dados de treino e de teste: confira os datasets, monte o dataset e avalie as configurações no conjunto de teste.'),
    corpo);

  async function recarregar() {
    await contexto.atualizarEstado();
    dados = await api.get('/api/datasets');
    desenhar();
  }

  async function executar(promessa, mensagemOk) {
    try {
      const resultado = await promessa;
      anunciar(mensagemOk);
      await recarregar();
      return resultado;
    } catch (erro) {
      await falhaDaApi(erro);
      return null;
    }
  }

  const tarefa = (filtro) => (contexto.estado?.tarefas || []).find(filtro);

  // O11.1 Conferir os datasets
  function conferir() {
    const ativas = dados.tarefas;
    const linhas = dados.datasets.map((d) => {
      const download = ativas.find((t) => t.alvo?.dataset === d.id);
      let acao;
      if (download) acao = h('div', {}, estado(download.estado), progresso(download.progresso.atual, download.progresso.total, download.progresso.texto));
      else if (d.bruto_disponivel) acao = h('span', { class: 'pequeno' }, 'Arquivos brutos guardados.');
      else if (d.pode_baixar) {
        acao = h('button', { type: 'button', class: 'botao botao-pequeno',
          onclick: () => executar(api.post(`/api/datasets/${enc(d.id)}/baixar`), `Download do ${d.nome} na fila.`) }, `Baixar ${d.nome}`);
      } else {
        acao = h('span', { class: 'pequeno' }, 'Copie a pasta CaSSed_Dataset (extraída do CaSSeD.tar.gz) para raw/CaSSed_Dataset.');
      }
      return h('tr', {},
        h('th', { scope: 'row' }, d.nome),
        h('td', {}, d.bruto_disponivel ? h('span', { class: 'marcador marcador-correta' }, '✓ disponível') : h('span', { class: 'marcador marcador-sem' }, 'ausente')),
        h('td', { class: 'numero' }, formato.inteiro(d.imagens_treino)),
        h('td', { class: 'numero' }, formato.inteiro(d.imagens_teste)),
        h('td', {}, acao));
    });

    const semAvaliacao = dados.configuracoes_a_avaliar;
    return h('section', { class: 'cartao', 'aria-labelledby': 'titulo-conferir' },
      h('h2', { id: 'titulo-conferir' }, 'Conferir os datasets'),
      h('div', { class: 'tabela-rolagem' }, h('table', {},
        h('caption', { class: 'oculto-visual' }, 'Datasets do TCC no dataset montado'),
        h('thead', {}, h('tr', {}, h('th', {}, 'Dataset'), h('th', {}, 'Arquivos brutos (raw/)'),
          h('th', { class: 'numero' }, 'Imagens de treino'), h('th', { class: 'numero' }, 'Imagens de teste'), h('th', {}, 'Ação'))),
        h('tbody', {}, linhas))),
      h('p', { style: 'margin-top:.75rem' }, h('strong', {}, 'Conjunto de teste', ' atual: '),
        dados.conjunto_de_teste ? conjuntoTexto(dados.conjunto_de_teste) : 'nenhum (monte o dataset).'),
      h('p', {}, h('strong', {}, 'Sem avaliação no conjunto de teste', ': '),
        semAvaliacao.length ? semAvaliacao.map((c) => `${c.nome} (${c.motivo})`).join('; ') : 'nenhuma configuração.'));
  }

  // O11.2 Montar o dataset
  function montar() {
    const ativa = dados.tarefas.find((t) => t.alvo?.dataset === 'todos');
    const ultima = dados.ultima_montagem;
    const brutos = dados.datasets.filter((d) => d.bruto_disponivel);
    const partes = [
      h('h2', { id: 'titulo-montar' }, 'Montar o dataset'),
      dados.montagem ? h('p', {}, `Última montagem: ${formato.data(dados.montagem.data)}${dados.montagem.datasets?.length ? `, com ${dados.montagem.datasets.join(', ')}` : ''}.`)
        : h('p', {}, 'O dataset ainda não foi montado pela interface.'),
    ];

    if (ativa) {
      partes.push(h('div', {}, h('div', { class: 'linha' }, h('strong', {}, 'Montagem do dataset'), estado(ativa.estado)),
        ativa.estado === 'na fila' ? h('p', { class: 'pequeno' }, 'Aguardando a vez: os processamentos rodam um de cada vez.')
          : progresso(ativa.progresso.atual, ativa.progresso.total, ativa.progresso.texto)));
    } else {
      if (montagemPedida && ultima?.estado === 'concluído') {
        partes.push(mensagem('ok', h('p', {}, h('strong', {}, 'Dataset montado. '), 'Confira acima as imagens de cada dataset e o conjunto de teste atual.')));
      }
      if (montagemPedida && ultima?.estado === 'falhou') {
        partes.push(mensagem('falha', h('p', {}, h('strong', {}, 'Falhou: '), `a montagem do dataset não terminou porque ${ultima.causa}.`),
          ultima.sugestao ? h('p', {}, ultima.sugestao) : null));
      }
      partes.push(h('button', { type: 'button', class: 'botao', disabled: !brutos.length, onclick: confirmarMontagem }, 'Remontar'));
    }
    return h('section', { class: 'cartao', 'aria-labelledby': 'titulo-montar' }, partes);
  }

  async function confirmarMontagem() {
    // Alerta "Confirmar a remontagem" (AL)
    const escolha = await dialogo({
      tipo: 'alerta', titulo: 'Confirmar a remontagem',
      corpo: h('div', {},
        h('p', {}, 'O conjunto de teste pode mudar, e as configurações avaliadas terão de ser avaliadas de novo.'),
        h('p', { class: 'pequeno' }, 'O dataset montado é substituído por uma nova cópia dos arquivos brutos (raw/), que não mudam.')),
      acoes: [{ rotulo: 'Cancelar', valor: 'cancelar' }, { rotulo: 'Confirmar', valor: 'confirmar', primaria: true }],
    });
    if (escolha === 'confirmar') {
      montagemPedida = true;
      await executar(api.post('/api/datasets/remontar'), 'Montagem do dataset na fila.');
    }
  }

  // O11.3 Avaliar as configurações no conjunto de teste
  function avaliar() {
    const lista = dados.avaliacoes.filter((a) => pedidas.has(a.id) || ['na fila', 'processando', 'falhou'].includes(a.estado));
    const partes = [h('h2', { id: 'titulo-avaliar' }, 'Avaliar as configurações no ', 'conjunto de teste')];

    if (dados.configuracoes_a_avaliar.length) {
      const botao = h('button', { type: 'submit', class: 'botao' }, 'Avaliar as selecionadas');
      const form = h('form', { novalidate: true },
        h('fieldset', { 'data-campo': 'configuracoes' },
          h('legend', {}, 'Configurações sem avaliação no conjunto de teste atual'),
          dados.configuracoes_a_avaliar.map((c) => h('label', { class: 'opcao' },
            h('input', { type: 'checkbox', name: 'configuracoes', value: c.id }),
            h('span', {}, c.nome, h('span', { class: 'pequeno suave' }, ` · ${c.motivo}`))))),
        h('div', { class: 'linha' }, botao));
      exigir(form, botao, [
        { campo: 'configuracoes', valido: () => form.querySelectorAll('input:checked').length > 0 },
      ]);
      form.addEventListener('submit', async (evento) => {
        evento.preventDefault();
        const configuracoes = new FormData(form).getAll('configuracoes');
        if (!configuracoes.length) return;
        configuracoes.forEach((cid) => pedidas.add(cid));
        await executar(api.post('/api/datasets/avaliar', { configuracoes }), 'Avaliação na fila.');
      });
      partes.push(form);
    } else if (!lista.length) {
      partes.push(h('p', {}, 'Todas as configurações disponíveis estão avaliadas no conjunto de teste atual.'));
    }

    if (lista.length) {
      partes.push(h('h3', { style: 'margin-top:1rem' }, 'Estado das avaliações'),
        h('ul', { class: 'lista-avaliacoes', 'aria-live': 'polite' }, lista.map((a) => linhaAvaliacao(a))));
      const todasConcluidas = [...pedidas].length > 0
        && [...pedidas].every((cid) => dados.avaliacoes.find((a) => a.id === cid)?.estado === 'concluída');
      if (todasConcluidas) {
        partes.push(mensagem('ok', h('p', {}, h('strong', {}, 'Avaliação concluída. '), 'As configurações avaliadas já podem entrar na comparação de desempenho.')));
      }
    }
    return h('section', { class: 'cartao', 'aria-labelledby': 'titulo-avaliar' }, partes);
  }

  function linhaAvaliacao(a) {
    const emCurso = tarefa((t) => t.tipo === 'avaliacao' && t.alvo?.configuracao === a.id);
    const itens = [h('div', { class: 'linha-entre' }, h('strong', {}, a.nome), estado(a.estado))];
    if (a.estado === 'na fila') itens.push(h('p', { class: 'pequeno' }, 'Aguardando a vez: as configurações são avaliadas uma de cada vez.'));
    if (a.estado === 'processando' && emCurso) itens.push(progresso(emCurso.progresso.atual, emCurso.progresso.total, emCurso.progresso.texto));
    if (a.estado === 'falhou') {
      // RA: tentar de novo aqui; CE: o que fazer fora do sistema
      itens.push(mensagem('falha',
        h('p', {}, h('strong', {}, 'Falhou: '), `a avaliação da ${a.nome} não terminou porque ${a.causa}.`),
        a.sugestao ? h('p', {}, h('strong', {}, a.tipo_falha === 'CE' ? 'O que fazer: ' : 'Sugestão: '), a.sugestao) : null,
        h('button', { type: 'button', class: 'botao botao-pequeno', onclick: () => {
          pedidas.add(a.id);
          executar(api.post(`/api/configuracoes/${enc(a.id)}/avaliar`), 'Avaliação pedida de novo.');
        } }, 'Tentar de novo')));
    }
    return h('li', { class: 'cartao', style: 'box-shadow:none' }, itens);
  }

  function desenhar() {
    // Falhas recentes de download: causa e o que fazer
    const falhas = (dados.tarefas_recentes || []).filter((t) => t.estado === 'falhou' && t.alvo?.dataset && t.alvo.dataset !== 'todos');
    limpar(corpo,
      falhas.map((t) => mensagem('falha', h('p', {}, h('strong', {}, 'Falhou: '), `${t.titulo} não terminou porque ${t.causa}.`),
        t.sugestao ? h('p', {}, t.sugestao) : null)),
      conferir(), montar(), avaliar());
  }

  desenhar();

  let ultimo = '';
  return {
    async atualizar(estadoGeral) {
      const ativas = (estadoGeral?.tarefas || []).filter((t) => t.tipo === 'dataset' || t.tipo === 'avaliacao')
        .map((t) => [t.id, t.estado, t.progresso.atual, t.progresso.texto]);
      const chave = JSON.stringify(ativas);
      if (chave === ultimo) return;
      ultimo = chave;
      dados = await api.get('/api/datasets');
      desenhar();
    },
  };
}
