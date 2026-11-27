// O03.1 Enviar as entradas e escolher as configurações (M01 e M03).
// Ruptura: arquivos em formato não aceito → alerta com "trocar os arquivos" ou "seguir sem eles" (os aceitos entram na fila).
import { api, ErroApi } from '../api.js';
import { h, limpar, cabecalho, mensagem, dialogo, falhaDaApi, erroCampo, exigir, anunciar } from '../ui.js';
import { seletorDeConfiguracoes } from './comum.js';

const ACEITOS = ['.jpg', '.jpeg', '.png', '.mp4'];
const FORMATOS = 'imagens JPG ou PNG e vídeos MP4 (o sistema extrai os quadros dos vídeos)';

function extensao(nome) {
  const ponto = nome.lastIndexOf('.');
  return ponto >= 0 ? nome.slice(ponto).toLowerCase() : '';
}

export async function render(main, _parametros, consulta, contexto) {
  const [configuracoes, ciclos] = await Promise.all([api.get('/api/configuracoes'), api.get('/api/ciclos')]);
  const disponiveis = configuracoes.filter((c) => c.disponivel);
  const preSelecionadas = (consulta.get('configuracoes') || '').split(',').filter(Boolean);
  let arquivos = [];
  let regras = null;

  limpar(main, cabecalho('Segmentar imagens', 'Envie as imagens do teste e escolha com quais configurações segmentar.'));

  if (!disponiveis.length) {
    main.append(mensagem('alerta',
      h('p', {}, 'Ainda não há configuração treinada para segmentar.'),
      h('p', {}, h('a', { href: '#/treino/novo' }, 'Treine uma configuração'), ' ou peça a quem treina os modelos.')));
    return;
  }

  const campoCiclo = h('input', {
    type: 'text', id: 'ciclo', list: 'ciclos-existentes', autocomplete: 'off', required: true,
    value: '', placeholder: 'ex.: Teste de 15/11/2026',
  });
  const listaArquivos = h('ul', { class: 'lista-arquivos', 'aria-live': 'polite' });
  const entradaArquivos = h('input', { type: 'file', id: 'arquivos', multiple: true, accept: ACEITOS.join(','), class: 'oculto-visual' });
  const zona = h('div', { class: 'zona-envio' },
    h('p', {}, h('strong', {}, 'Arraste as imagens ou os vídeos para cá'), ' ou'),
    h('label', { for: 'arquivos', class: 'botao botao-secundario', tabindex: '0', role: 'button',
      onkeydown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); entradaArquivos.click(); } } }, 'Escolher arquivos'),
    entradaArquivos,
    h('p', { class: 'pequeno suave', style: 'margin-top:.6rem' },
      `Formatos aceitos: ${FORMATOS}. Cada quadro de um vídeo vira uma imagem da sessão.`));

  const seletor = seletorDeConfiguracoes(disponiveis, {
    nome: 'configuracoes', selecionadas: preSelecionadas.length ? preSelecionadas : [], rotulo: 'Configurações disponíveis',
  });

  function desenharArquivos() {
    limpar(listaArquivos, arquivos.map((arquivo, indice) => h('li', {},
      h('span', {}, arquivo.name, ACEITOS.includes(extensao(arquivo.name)) ? '' : h('strong', { style: 'color:var(--falha)' }, ' (formato não aceito)')),
      h('button', {
        type: 'button', class: 'botao-link', 'aria-label': `Retirar ${arquivo.name} da lista`,
        onclick: () => { arquivos.splice(indice, 1); desenharArquivos(); },
      }, 'Retirar'))));
    contador.textContent = arquivos.length ? `${arquivos.length} arquivo(s) escolhido(s).` : 'Nenhum arquivo escolhido.';
    regras?.atualizar();
  }

  function adicionarArquivos(lista) {
    const nomes = new Set(arquivos.map((a) => `${a.name}-${a.size}`));
    for (const arquivo of lista) if (!nomes.has(`${arquivo.name}-${arquivo.size}`)) arquivos.push(arquivo);
    desenharArquivos();
  }

  entradaArquivos.addEventListener('change', () => { adicionarArquivos(entradaArquivos.files); entradaArquivos.value = ''; });
  zona.addEventListener('dragover', (e) => { e.preventDefault(); zona.classList.add('arrastando'); });
  zona.addEventListener('dragleave', () => zona.classList.remove('arrastando'));
  zona.addEventListener('drop', (e) => { e.preventDefault(); zona.classList.remove('arrastando'); adicionarArquivos(e.dataTransfer.files); });

  const contador = h('p', { class: 'pequeno suave' }, 'Nenhum arquivo escolhido.');
  const botaoExecutar = h('button', { type: 'submit', class: 'botao' }, 'Executar');

  const formulario = h('form', { novalidate: true },
    h('div', { class: 'grade-2' },
      h('div', {},
        h('div', { class: 'cartao' },
          h('h2', {}, '1. Imagens'),
          h('div', { class: 'campo', 'data-campo': 'ciclo' },
            h('label', { for: 'ciclo' }, 'Ciclo de testes'),
            h('span', { class: 'ajuda', id: 'ajuda-ciclo' }, 'O nome ou a data do teste de campo destas imagens.'),
            campoCiclo,
            h('datalist', { id: 'ciclos-existentes' }, ciclos.map((c) => h('option', { value: c.ciclo })))),
          h('div', { class: 'campo', 'data-campo': 'arquivos' }, h('span', { class: 'rotulo' }, 'Imagens ou vídeos'), zona, contador, listaArquivos))),
      h('div', {},
        h('div', { class: 'cartao' },
          h('h2', {}, '2. ', 'Configurações'),
          h('p', { class: 'pequeno suave' }, 'Escolha uma ou mais. Com mais de uma, os resultados abrem lado a lado na mesma imagem.'),
          h('div', { 'data-campo': 'configuracoes' }, seletor.elemento)))),
    h('div', { class: 'linha' }, botaoExecutar));

  main.append(formulario);

  // Campos obrigatórios: o botão fica desabilitado até tudo estar preenchido
  regras = exigir(formulario, botaoExecutar, [
    { campo: 'ciclo', valido: () => campoCiclo.value.trim().length > 0 },
    { campo: 'arquivos', valido: () => arquivos.length > 0 },
    { campo: 'configuracoes', valido: () => seletor.valores().length > 0 },
  ]);

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    erroCampo(formulario, null);

    if (!regras.atualizar()) return;
    const ciclo = campoCiclo.value.trim();
    const escolhidas = seletor.valores();

    // Ruptura prevista: formato não aceito, avisado antes de começar
    const recusados = arquivos.filter((a) => !ACEITOS.includes(extensao(a.name)));
    const aceitos = arquivos.filter((a) => ACEITOS.includes(extensao(a.name)));
    if (recusados.length) {
      const seguir = await alertaFormato(recusados.map((a) => a.name), arquivos.length, aceitos.length);
      if (seguir !== 'seguir') return;
    }

    botaoExecutar.disabled = true;
    botaoExecutar.textContent = 'Enviando os arquivos: 0%';
    let anunciado = 0;
    try {
      const dados = new FormData();
      dados.append('ciclo', ciclo);
      aceitos.forEach((arquivo) => dados.append('arquivos', arquivo, arquivo.name));
      const resposta = await api.enviar('/api/sessoes', dados, (enviado, total) => {
        const porcentagem = Math.floor((100 * enviado) / total);
        botaoExecutar.textContent = porcentagem >= 100 ? 'Conferindo os arquivos…' : `Enviando os arquivos: ${porcentagem}%`;
        if (porcentagem >= anunciado + 25) { anunciado = porcentagem - (porcentagem % 25); anunciar(`Enviando os arquivos: ${anunciado}%`); }
      });

      // O servidor também confere o conteúdo: arquivos corrompidos voltam aqui
      if (resposta.recusadas.length) {
        const total = aceitos.length;
        const seguiram = total - resposta.recusadas.length;
        const decisao = await alertaFormato(resposta.recusadas.map((r) => `${r.nome} (${r.motivo})`), total, seguiram, true);
        if (decisao !== 'seguir') {
          if (resposta.sessao) await api.delete(`/api/sessoes/${encodeURIComponent(resposta.sessao.id)}/rascunho`);
          return;
        }
      }

      const sessao = await api.post(`/api/sessoes/${encodeURIComponent(resposta.sessao.id)}/executar`, { configuracoes: escolhidas });
      contexto.navegar(`#/sessao/${encodeURIComponent(sessao.id)}/processamento`);
    } catch (erro) {
      if (erro instanceof ErroApi && erro.tipo === 'PA') erroCampo(formulario, erro);
      else await falhaDaApi(erro, 'Não foi possível executar');
    } finally {
      botaoExecutar.textContent = 'Executar';
      regras.atualizar();
    }
  });
}

async function alertaFormato(nomes, total, restantes, ilegiveis = false) {
  const corpo = h('div', {},
    h('p', {}, `${nomes.length} de ${total} arquivo(s) ${ilegiveis ? 'não puderam ser lidos' : 'não estão em um formato aceito'}:`),
    h('ul', {}, nomes.slice(0, 12).map((nome) => h('li', {}, nome)), nomes.length > 12 ? h('li', {}, `e mais ${nomes.length - 12}`) : null),
    h('p', {}, `Formatos aceitos: ${FORMATOS}.`),
    restantes > 0
      ? h('p', {}, `Quer seguir sem eles (os outros ${restantes} entram na fila) ou trocar esses arquivos antes?`)
      : h('p', {}, 'Nenhum arquivo pode ser segmentado assim. Troque os arquivos para continuar.'));

  return dialogo({
    tipo: 'alerta',
    titulo: ilegiveis ? 'Arquivos que não puderam ser lidos' : 'Arquivos fora do formato aceito',
    corpo,
    acoes: restantes > 0
      ? [{ rotulo: 'Trocar os arquivos', valor: 'trocar' }, { rotulo: 'Seguir sem eles', valor: 'seguir', primaria: true }]
      : [{ rotulo: 'Trocar os arquivos', valor: 'trocar', primaria: true }],
  });
}
