// Roteamento por hash, atualização periódica do estado e acessos ubíquos
// ("Em que ponto está o treino?" e "O que é este termo?").
import { api } from './api.js';
import { h, limpar, mensagem, icone } from './ui.js';
import { abrirTermo, fecharTermo } from './glossario.js';

import * as segmentar from './telas/segmentar.js';
import * as processamento from './telas/processamento.js';
import * as sessao from './telas/sessao.js';
import * as comparacao from './telas/comparacao.js';
import * as treino from './telas/treino.js';
import * as desempenho from './telas/desempenho.js';
import * as conclusao from './telas/conclusao.js';
import * as apresentacao from './telas/apresentacao.js';
import * as datasets from './telas/datasets.js';

const ROTAS = [
  ['segmentar', segmentar.render, 'segmentar'],
  ['sessao', sessao.renderAtual, 'sessao'],
  ['sessao/:id/processamento', processamento.render, 'sessao'],
  ['sessao/:id/imagem', sessao.render, 'sessao'],
  ['sessao/:id/escolher-comparacao', comparacao.renderEscolher, 'sessao'],
  ['sessao/:id/comparar', comparacao.renderComparar, 'sessao'],
  ['treino/novo', treino.renderNovo, 'treino'],
  ['treino/:id', treino.renderAcompanhar, 'treino'],
  ['desempenho', desempenho.render, 'desempenho'],
  ['conclusao/nova', conclusao.renderNova, null],
  ['conclusao/:id/corrigir', conclusao.renderCorrigir, null],
  ['conclusao/:id', conclusao.renderConferir, null],
  ['apresentar', apresentacao.render, 'apresentar'],
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
  fecharTermo();

  const { caminho, consulta } = separar(location.hash);
  if (!caminho) {
    await atualizarEstado();
    contexto.navegar(contexto.estado?.ultima_sessao ? '#/sessao' : '#/segmentar');
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

// Acesso ubíquo do M03: "Em que ponto está o treino?"
function desenharIndicador(estado) {
  const botao = document.getElementById('indicador-treino');
  const recente = estado?.treino_recente;
  if (!recente) { botao.hidden = true; return; }

  let texto;
  let nomeIcone;
  if (recente.estado === 'treinando') {
    const etapa = recente.etapa === 'Avaliando no conjunto de teste' ? 'avaliando no conjunto de teste'
      : `época ${recente.epoca || 0} de ${recente.total || '?'}`;
    texto = `Treinando: ${recente.nome} · ${etapa}`;
    nomeIcone = 'andamento';
  } else if (recente.estado === 'na fila') {
    texto = `Treino na fila: ${recente.nome}`;
    nomeIcone = 'fila';
  } else if (recente.estado === 'falhou') {
    texto = `Treino interrompido: ${recente.nome}`;
    nomeIcone = 'falha';
  } else {
    texto = `Treino concluído: ${recente.nome}`;
    nomeIcone = 'ok';
  }

  botao.hidden = false;
  limpar(botao, icone(nomeIcone), h('span', {}, texto));
  botao.setAttribute('aria-label', `Em que ponto está o treino? ${texto}`);
  botao.title = 'Em que ponto está o treino?';
  botao.onclick = () => contexto.navegar(`#/treino/${encodeURIComponent(recente.id)}`);
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

document.getElementById('abrir-glossario').addEventListener('click', (evento) => abrirTermo(null, evento.currentTarget));
document.getElementById('fechar-termo').addEventListener('click', fecharTermo);
document.addEventListener('keydown', (evento) => {
  if (evento.key === 'Escape' && !document.getElementById('painel-termo').hidden) fecharTermo();
});

window.addEventListener('hashchange', rotear);
atualizarEstado().then(rotear);
setInterval(ciclo, 2000);
