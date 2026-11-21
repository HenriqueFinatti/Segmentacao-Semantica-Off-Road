// Componentes de interface usados por todas as telas.
import { abrirExplicacao } from './glossario.js';

export function h(tag, atributos = {}, ...filhos) {
  const elemento = document.createElement(tag);

  for (const [chave, valor] of Object.entries(atributos || {})) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (chave === 'class') elemento.className = valor;
    else if (chave === 'html') elemento.innerHTML = valor;
    else if (chave.startsWith('on') && typeof valor === 'function') elemento.addEventListener(chave.slice(2).toLowerCase(), valor);
    else if (valor === true) elemento.setAttribute(chave, '');
    else elemento.setAttribute(chave, valor);
  }

  adicionar(elemento, filhos);
  return elemento;
}

function adicionar(elemento, filhos) {
  for (const filho of filhos.flat(Infinity)) {
    if (filho === null || filho === undefined || filho === false) continue;
    elemento.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
}

export function limpar(elemento, ...filhos) {
  elemento.replaceChildren();
  adicionar(elemento, filhos);
  return elemento;
}

// Ícones simples (decorativos: o texto ao lado sempre diz o mesmo)
const ICONES = {
  ok: '<path d="M4 10.5l4 4 8-9" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
  falha: '<path d="M10 2.5l8.5 15h-17z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M10 8v4.5M10 15v.2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
  alerta: '<circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" stroke-width="2"/><path d="M10 5.5v5.5M10 14v.2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
  info: '<circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" stroke-width="2"/><path d="M10 9v5.5M10 6v.2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
  andamento: '<path d="M10 2.5a7.5 7.5 0 1 1-7.5 7.5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>',
  fila: '<circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" stroke-width="2"/><path d="M10 5.5V10l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  sem: '<circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3"/>',
};

export function icone(nome) {
  const span = document.createElement('span');
  span.setAttribute('aria-hidden', 'true');
  span.style.display = 'inline-flex';
  span.innerHTML = `<svg viewBox="0 0 20 20" width="18" height="18" focusable="false">${ICONES[nome] || ICONES.info}</svg>`;
  return span.firstChild;
}

const ESTADOS = {
  'na fila': ['estado-fila', 'fila', 'Na fila'],
  processando: ['estado-andamento', 'andamento', 'Processando'],
  treinando: ['estado-andamento', 'andamento', 'Treinando'],
  'concluído': ['estado-concluido', 'ok', 'Concluído'],
  'concluída': ['estado-concluido', 'ok', 'Concluída'],
  falhou: ['estado-falhou', 'falha', 'Falhou'],
};

export function estado(valor, texto) {
  const [classe, nomeIcone, rotulo] = ESTADOS[valor] || ['estado-fila', 'info', valor || '—'];
  return h('span', { class: `estado ${classe}` }, icone(nomeIcone), texto || rotulo);
}

export function situacao(valor) {
  const classe = valor === 'em uso' ? 'situacao-em-uso' : valor === 'candidata' ? 'situacao-candidata' : '';
  return h('span', { class: `situacao ${classe}` }, valor);
}

export function mensagem(tipo, ...conteudo) {
  const icones = { info: 'info', ok: 'ok', alerta: 'alerta', falha: 'falha', neutra: 'info' };
  return h('div', { class: `mensagem mensagem-${tipo}`, role: tipo === 'falha' ? 'alert' : null },
    icone(icones[tipo]), h('div', {}, ...conteudo));
}

export function anunciar(texto) {
  const regiao = document.getElementById('aviso-vivo');
  regiao.textContent = '';
  setTimeout(() => { regiao.textContent = texto; }, 50);
}

// Termo técnico com a explicação no ponto de uso (O07.1)
export function botaoTermo(rotulo, chave) {
  return h('button', {
    type: 'button',
    class: 'termo-ajuda',
    'aria-label': `O que é ${rotulo}?`,
    title: `O que é ${rotulo}?`,
    'aria-expanded': 'false',
    onclick: (evento) => abrirExplicacao(chave, evento.currentTarget),
  }, '?');
}

export function termo(rotulo, chave) {
  return h('span', { class: 'termo' }, rotulo, botaoTermo(rotulo, chave));
}

// Rótulo ligado ao campo, com o "?" fora do <label> (o nome do campo não inclui o botão)
export function rotuloComTermo(paraId, rotulo, chave) {
  return h('span', { class: 'termo' }, h('label', { for: paraId }, rotulo), botaoTermo(rotulo, chave));
}

// Legenda fixa das classes (RQ04): o nome acompanha sempre a cor
export function legenda(modo = 'mascara') {
  return h('div', { class: 'legenda', role: 'group', 'aria-label': 'Legenda' },
    h('strong', {}, termo('Legenda', 'legenda'), ':'),
    h('span', { class: 'legenda-item' }, h('span', { class: 'amostra amostra-trilha', 'aria-hidden': 'true' }),
      modo === 'sobreposicao' ? 'Trilha (pintada, com contorno branco)' : 'Trilha'),
    h('span', { class: 'legenda-item' },
      h('span', { class: `amostra ${modo === 'sobreposicao' ? 'amostra-original' : 'amostra-fora'}`, 'aria-hidden': 'true' }),
      modo === 'sobreposicao' ? 'Fora da trilha (imagem original, sem pintura)' : 'Fora da trilha'));
}

export function progresso(atual, total, texto) {
  const porcentagem = total > 0 ? Math.min(100, Math.round((100 * atual) / total)) : 0;
  return h('div', { class: 'progresso' },
    h('span', { class: 'pequeno' }, texto || (total ? `${atual} de ${total}` : '')),
    total > 0 ? h('div', {
      class: 'progresso-barra', role: 'progressbar', 'aria-valuemin': '0', 'aria-valuemax': String(total),
      'aria-valuenow': String(atual), 'aria-label': texto || 'Progresso',
    }, h('span', { style: `width:${porcentagem}%` })) : null);
}

// Diálogo modal para alertas e falhas: devolve o valor da ação escolhida
export function dialogo({ tipo = 'alerta', titulo, corpo, acoes }) {
  const elemento = document.getElementById('dialogo');
  const icones = { alerta: ['alerta', 'var(--alerta)'], falha: ['falha', 'var(--falha)'], info: ['info', 'var(--andamento)'], ok: ['ok', 'var(--ok)'] };
  const [nomeIcone, cor] = icones[tipo] || icones.info;

  const caixaIcone = document.getElementById('dialogo-icone');
  limpar(caixaIcone, icone(nomeIcone));
  caixaIcone.style.color = cor;
  document.getElementById('dialogo-titulo').textContent = titulo;
  limpar(document.getElementById('dialogo-corpo'), corpo);

  const anterior = document.activeElement;
  return new Promise((resolver) => {
    const botoes = acoes.map((acao) => h('button', {
      type: 'button',
      class: `botao ${acao.primaria ? '' : 'botao-secundario'}`,
      onclick: () => { elemento.close(); resolver(acao.valor); },
    }, acao.rotulo));
    limpar(document.getElementById('dialogo-acoes'), botoes);

    elemento.onclose = () => {
      resolver(null);
      if (anterior && document.body.contains(anterior)) anterior.focus();
    };
    elemento.showModal();
    (botoes.find((_, i) => acoes[i].primaria) || botoes[0]).focus();
  });
}

export function falhaDaApi(erro, titulo = 'Não foi possível concluir') {
  return dialogo({
    tipo: 'falha',
    titulo,
    corpo: h('p', {}, erro.message),
    acoes: [{ rotulo: 'Entendi', valor: 'ok', primaria: true }],
  });
}

// Formatação em português

const decimal = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const inteiro = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
const porcento = new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 });

export const formato = {
  metrica: (valor) => (valor === null || valor === undefined ? '—' : decimal.format(valor)),
  diferenca: (valor) => (valor === null || valor === undefined ? '—' : `${valor > 0 ? '+' : valor < 0 ? '−' : ''}${decimal.format(Math.abs(valor))}`),
  ms: (valor) => (valor === null || valor === undefined ? '—' : `${inteiro.format(valor)} ms`),
  inteiro: (valor) => inteiro.format(valor),
  porcento: (valor) => (valor === null || valor === undefined || Number.isNaN(valor) ? '—' : porcento.format(valor)),
  data: (iso) => {
    if (!iso) return '—';
    const data = new Date(iso);
    return Number.isNaN(data.getTime()) ? iso : data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  },
};

export function conjuntoTexto(conjunto) {
  if (!conjunto) return 'sem conjunto de teste';
  const partes = Object.entries(conjunto.por_dataset || {}).map(([nome, n]) => `${nome}: ${n}`).join(', ');
  const data = conjunto.montado_em ? `, montado em ${formato.data(conjunto.montado_em)}` : '';
  return `conjunto de teste ${conjunto.id} (${conjunto.imagens} imagens${partes ? ` — ${partes}` : ''}${data})`;
}

export function cabecalho(titulo, sub, trilha) {
  return h('div', { class: 'cabecalho-tela' },
    trilha ? h('div', { class: 'trilha-navegacao' }, trilha) : null,
    h('h1', { tabindex: '-1', id: 'titulo-tela' }, titulo),
    sub ? h('p', { class: 'sub' }, sub) : null);
}

export function erroCampo(formulario, erro) {
  formulario.querySelectorAll('.erro-campo').forEach((el) => el.remove());
  formulario.querySelectorAll('[aria-invalid]').forEach((el) => el.removeAttribute('aria-invalid'));
  if (!erro) return;

  const alvo = erro.campo && formulario.querySelector(`[data-campo="${erro.campo}"]`);
  const aviso = h('p', { class: 'erro-campo', id: `erro-${erro.campo || 'geral'}`, role: 'alert' }, erro.message);

  if (alvo) {
    alvo.append(aviso);
    const entrada = alvo.querySelector('input, select, textarea');
    if (entrada) {
      entrada.setAttribute('aria-invalid', 'true');
      entrada.setAttribute('aria-describedby', aviso.id);
      entrada.focus();
    }
  } else {
    formulario.prepend(aviso);
  }
}

/**
 * Campo obrigatório com o mesmo comportamento em todas as telas: enquanto falta algo, o botão fica
 * desabilitado e, junto do campo, uma mensagem diz o que falta (prevenção ativa).
 * regras: [{ campo: 'nome do data-campo', valido: () => bool, mensagem: 'o que falta' }]
 */
export function exigir(formulario, botao, regras) {
  const resumo = h('p', { class: 'falta-resumo', id: `falta-resumo-${Math.random().toString(36).slice(2, 8)}`, 'aria-live': 'polite' });
  botao.insertAdjacentElement('afterend', resumo);

  function atualizar() {
    const faltando = [];
    for (const regra of regras) {
      const recipiente = formulario.querySelector(`[data-campo="${regra.campo}"]`);
      if (!recipiente) continue;
      let aviso = recipiente.querySelector(`:scope > .falta-campo`);
      const valido = regra.valido();
      if (!valido) {
        faltando.push(regra.mensagem);
        if (!aviso) {
          aviso = h('p', { class: 'falta-campo', id: `falta-${regra.campo}` });
          recipiente.append(aviso);
        }
        aviso.textContent = regra.mensagem;
        recipiente.querySelectorAll('input, select, textarea').forEach((entrada) => {
          const atuais = (entrada.getAttribute('aria-describedby') || '').split(' ').filter(Boolean);
          if (!atuais.includes(aviso.id)) entrada.setAttribute('aria-describedby', [...atuais, aviso.id].join(' '));
        });
      } else if (aviso) {
        recipiente.querySelectorAll('input, select, textarea').forEach((entrada) => {
          const atuais = (entrada.getAttribute('aria-describedby') || '').split(' ').filter((x) => x && x !== aviso.id);
          if (atuais.length) entrada.setAttribute('aria-describedby', atuais.join(' '));
          else entrada.removeAttribute('aria-describedby');
        });
        aviso.remove();
      }
    }
    botao.disabled = faltando.length > 0;
    resumo.textContent = faltando.length ? `Para continuar: ${faltando.join(' ')}` : '';
    if (faltando.length) botao.setAttribute('aria-describedby', resumo.id);
    else botao.removeAttribute('aria-describedby');
    return faltando.length === 0;
  }

  formulario.addEventListener('input', atualizar);
  formulario.addEventListener('change', atualizar);
  atualizar();
  return { atualizar };
}
