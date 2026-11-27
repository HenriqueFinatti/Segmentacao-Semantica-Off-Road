// Roteamento por hash, atualização periódica do estado e acessos ubíquos
// ("Em que ponto está o treino?").
import { api } from './api.js';
import { h, limpar, mensagem, icone } from './ui.js';

import * as segmentar from './telas/segmentar.js';
import * as processamento from './telas/processamento.js';
import * as sessao from './telas/sessao.js';
import * as treino from './telas/treino.js';
import * as desempenho from './telas/desempenho.js';
import * as datasets from './telas/datasets.js';

const ROTAS = [
  ['segmentar', segmentar.render, 'segmentar'],
  ['sessao', sessao.renderAtual, 'sessao'],
  ['sessao/:id/processamento', processamento.render, 'sessao'],
  ['sessao/:id/imagem', sessao.render, 'sessao'],
  ['treino/novo', treino.renderNovo, 'treino'],
  ['treino/:id', treino.renderAcompanhar, 'treino'],
  ['desempenho', desempenho.render, 'desempenho'],
  ['datasets', datasets.render, 'datasets'],
];

const main = document.getElementById('conteudo');
const contexto = {
  estado: null,
  navegar: (destino) => { location.hash = destino; },
  atualizarEstado: () => atualizarEstado(),
};

let telaAtual = null;
let geracao = 0;

function separar(hash) {
  const [caminho, consulta = ''] = hash.replace(/^#\/?/, '').split('?');
  return { caminho: caminho.replace(/\/$/, ''), consulta: new URLSearchParams(consulta) };
}

function casar(padrao, caminho) {
  const partes = padrao.split('/');
  const valores = caminho.split('/').map(decodeURIComponent);
  if (partes.length !== valores.length) return null;
  const parametros = {};
  for (let i = 0; i < partes.length; i++) {
    if (partes[i].startsWith(':')) parametros[partes[i].slice(1)] = valores[i];
    else if (partes[i] !== valores[i]) return null;
  }
  return parametros;
}

async function rotear() {
  const minhaGeracao = ++geracao;
  telaAtual?.sair?.();
  telaAtual = null;

  const { caminho, consulta } = separar(location.hash);
  if (!caminho) {
    // A interface sempre começa limpa, em Segmentar imagens (a última sessão continua em "Sessão atual")
    contexto.navegar('#/segmentar');
    return;
  }

  for (const [padrao, render, menu] of ROTAS) {
    const parametros = casar(padrao, caminho);
    if (!parametros) continue;

    marcarMenu(menu);
    limpar(main, h('p', { class: 'suave' }, 'Carregando…'));

    try {
      const tela = await render(main, parametros, consulta, contexto);
      if (minhaGeracao !== geracao) { tela?.sair?.(); return; }
      telaAtual = tela || null;
    } catch (erro) {
      console.error(erro);
      if (minhaGeracao !== geracao) return;
      limpar(main, mensagem('falha', h('p', {}, erro.message || 'Não foi possível abrir esta tela.'),
        h('p', {}, h('a', { href: '#/segmentar' }, 'Voltar para Segmentar imagens'))));
    }

    const titulo = main.querySelector('#titulo-tela');
    window.scrollTo(0, 0);
    (titulo || main).focus({ preventScroll: true });
    if (titulo) document.title = `${titulo.textContent} · Segmentação Off-Road`;
    return;
  }

  limpar(main, mensagem('neutra', h('p', {}, 'Esta tela não existe.'), h('a', { href: '#/segmentar' }, 'Ir para Segmentar imagens')));
}

function marcarMenu(rota) {
  document.querySelectorAll('.navegacao a').forEach((link) => {
    if (link.dataset.rota === rota) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
}

// Acesso ubíquo do M03: "Em que ponto está o treino?", sempre visível
function desenharIndicador(estado) {
  const botao = document.getElementById('indicador-treino');
  const recente = estado?.treino_recente;
  botao.hidden = false;

  let texto;
  let nomeIcone;
  if (!recente) {
    texto = 'Nenhum treino em andamento';
    nomeIcone = 'sem';
  } else if (recente.estado === 'treinando') {
    texto = `Treinando: ${recente.nome} · época ${recente.epoca || 0}${recente.total ? ` de ${recente.total}` : ''}`;
    nomeIcone = 'andamento';
  } else if (recente.estado === 'na fila') {
    texto = `Treino na fila: ${recente.nome}`;
    nomeIcone = 'fila';
  } else if (recente.estado === 'falhou' || recente.avaliacao === 'falhou') {
    texto = `Treino ou avaliação interrompidos: ${recente.nome}`;
    nomeIcone = 'falha';
  } else if (recente.avaliacao === 'na fila' || recente.avaliacao === 'processando') {
    texto = `Avaliação no conjunto de teste ${recente.avaliacao}: ${recente.nome}`;
    nomeIcone = recente.avaliacao === 'na fila' ? 'fila' : 'andamento';
  } else {
    texto = `Treino concluído: ${recente.nome}`;
    nomeIcone = 'ok';
  }

  limpar(botao, icone(nomeIcone), h('span', {}, texto));
  botao.setAttribute('aria-label', `Em que ponto está o treino? ${texto}`);
  botao.title = 'Em que ponto está o treino?';
  if (recente) {
    botao.removeAttribute('aria-disabled');
    botao.onclick = () => contexto.navegar(`#/treino/${encodeURIComponent(recente.id)}`);
  } else {
    botao.setAttribute('aria-disabled', 'true');
    botao.onclick = null;
  }

  const versao = document.getElementById('versao');
  if (estado?.versao && versao && !versao.textContent) {
    versao.textContent = estado.versao.commit
      ? `Versão ${estado.versao.commit}${estado.versao.alteracoes ? ' (com alterações não registradas no git)' : ''}`
      : 'Versão sem registro no git';
  }
}

async function atualizarEstado() {
  try {
    contexto.estado = await api.get('/api/estado');
    desenharIndicador(contexto.estado);
  } catch {
    // Sem servidor: a tela mostra o erro quando a pessoa agir
  }
  return contexto.estado;
}

async function ciclo() {
  const estado = await atualizarEstado();
  if (estado && telaAtual?.atualizar) {
    try { await telaAtual.atualizar(estado); } catch (erro) { console.error(erro); }
  }
}

window.addEventListener('hashchange', rotear);
atualizarEstado().then(rotear);
setInterval(ciclo, 2000);
