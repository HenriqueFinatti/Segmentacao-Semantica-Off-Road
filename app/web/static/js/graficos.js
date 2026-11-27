// Gráficos em SVG, sem bibliotecas externas (funciona sem internet). Todo gráfico vem acompanhado de tabela.
import { h, formato } from './ui.js';

const NS = 'http://www.w3.org/2000/svg';

function s(tag, atributos = {}, ...filhos) {
  const elemento = document.createElementNS(NS, tag);
  for (const [chave, valor] of Object.entries(atributos)) {
    if (valor !== undefined && valor !== null) elemento.setAttribute(chave, valor);
  }
  for (const filho of filhos.flat()) {
    if (filho === null || filho === undefined) continue;
    elemento.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return elemento;
}

const decimal = (v, casas = 2) => (Math.abs(v) >= 10 ? v.toFixed(0) : v.toFixed(casas)).replace('.', ',');

/**
 * Linhas por época. series: [{ nome, valores: [número|null], tracejada, cor }]
 * Treino em linha contínua e validação em linha tracejada: a diferença não depende só da cor.
 */
export function graficoDeLinhas({ titulo, series, epocas, rotuloY }) {
  const largura = 520;
  const altura = 230;
  const margem = { esquerda: 46, direita: 12, topo: 14, baixo: 34 };
  const valores = series.flatMap((serie) => serie.valores).filter((v) => v !== null && v !== undefined && Number.isFinite(v));
  if (!valores.length || !epocas.length) return null;

  let minimo = Math.min(...valores);
  let maximo = Math.max(...valores);
  if (minimo === maximo) { minimo -= 0.5; maximo += 0.5; }
  const folga = (maximo - minimo) * 0.08;
  minimo -= folga; maximo += folga;

  // Faixa estreita precisa de mais casas para os rótulos do eixo não se repetirem
  const casasEixo = maximo - minimo < 0.05 ? 3 : 2;
  const x = (i) => margem.esquerda + (epocas.length === 1 ? (largura - margem.esquerda - margem.direita) / 2
    : (i * (largura - margem.esquerda - margem.direita)) / (epocas.length - 1));
  const y = (v) => margem.topo + ((maximo - v) * (altura - margem.topo - margem.baixo)) / (maximo - minimo);

  const svg = s('svg', { viewBox: `0 0 ${largura} ${altura}`, class: 'grafico', role: 'img', 'aria-label': `${titulo}. Os valores estão na tabela das épocas.` });

  for (let i = 0; i <= 4; i++) {
    const valor = minimo + ((maximo - minimo) * i) / 4;
    svg.append(
      s('line', { class: 'grade', x1: margem.esquerda, x2: largura - margem.direita, y1: y(valor), y2: y(valor) }),
      s('text', { x: margem.esquerda - 6, y: y(valor) + 4, 'text-anchor': 'end', 'font-size': 11 }, decimal(valor, casasEixo)),
    );
  }

  const passo = Math.max(1, Math.ceil(epocas.length / 10));
  epocas.forEach((epoca, i) => {
    if (i % passo === 0 || i === epocas.length - 1) {
      svg.append(s('text', { x: x(i), y: altura - margem.baixo + 16, 'text-anchor': 'middle', 'font-size': 11 }, epoca));
    }
  });
  svg.append(
    s('line', { class: 'eixo', x1: margem.esquerda, x2: margem.esquerda, y1: margem.topo, y2: altura - margem.baixo }),
    s('line', { class: 'eixo', x1: margem.esquerda, x2: largura - margem.direita, y1: altura - margem.baixo, y2: altura - margem.baixo }),
    s('text', { x: (largura + margem.esquerda) / 2, y: altura - 4, 'text-anchor': 'middle', 'font-size': 12 }, 'Época'),
  );

  for (const serie of series) {
    const pontos = serie.valores.map((v, i) => (v === null || v === undefined || !Number.isFinite(v) ? null : [x(i), y(v)]));
    const caminho = pontos.reduce((texto, ponto, i) => {
      if (!ponto) return texto;
      const anterior = i > 0 && pontos[i - 1];
      return `${texto}${anterior ? 'L' : 'M'}${ponto[0].toFixed(1)},${ponto[1].toFixed(1)} `;
    }, '');
    svg.append(s('path', {
      d: caminho, fill: 'none', stroke: serie.cor, 'stroke-width': 2.5,
      'stroke-dasharray': serie.tracejada ? '7 5' : null,
    }));
    pontos.forEach((ponto) => {
      if (!ponto) return;
      svg.append(serie.tracejada
        ? s('rect', { x: ponto[0] - 3.5, y: ponto[1] - 3.5, width: 7, height: 7, fill: '#fff', stroke: serie.cor, 'stroke-width': 2 })
        : s('circle', { cx: ponto[0], cy: ponto[1], r: 3.5, fill: serie.cor }));
    });
  }

  const legenda = h('div', { class: 'legenda-grafico', 'aria-hidden': 'true' },
    series.map((serie) => {
      const amostra = s('svg', { viewBox: '0 0 30 10' },
        s('line', { x1: 0, x2: 30, y1: 5, y2: 5, stroke: serie.cor, 'stroke-width': 3, 'stroke-dasharray': serie.tracejada ? '6 4' : null }));
      return h('span', {}, amostra, serie.nome);
    }));

  return h('figure', { style: 'margin:0' }, h('figcaption', { class: 'rotulo' }, titulo), svg, legenda);
}

/**
 * Barras agrupadas por métrica, com o valor escrito em cada barra.
 * grupos: [{ rotulo, valores: [{ nome, valor }] }]
 */
export function graficoDeBarras({ titulo, grupos, nomes, cores }) {
  const largura = 640;
  const alturaBarra = 18;
  const espaco = 6;
  const margemEsquerda = 190;
  const alturaGrupo = nomes.length * (alturaBarra + espaco) + 18;
  const altura = grupos.length * alturaGrupo + 10;
  const svg = s('svg', { viewBox: `0 0 ${largura} ${altura}`, class: 'grafico', role: 'img', 'aria-label': `${titulo}. Os mesmos valores estão na tabela acima.` });
  const escala = (v) => (v * (largura - margemEsquerda - 70));

  grupos.forEach((grupo, g) => {
    const topo = g * alturaGrupo + 4;
    svg.append(s('text', { x: 0, y: topo + 12, 'font-size': 12.5, 'font-weight': 600 }, grupo.rotulo));
    grupo.valores.forEach((item, i) => {
      const y = topo + 18 + i * (alturaBarra + espaco);
      const valor = item.valor ?? 0;
      svg.append(
        s('text', { x: margemEsquerda - 6, y: y + 13, 'text-anchor': 'end', 'font-size': 11.5 }, item.nome.length > 28 ? `${item.nome.slice(0, 27)}…` : item.nome),
        s('rect', { x: margemEsquerda, y, width: Math.max(1, escala(Math.max(0, Math.min(1, valor)))), height: alturaBarra, fill: cores[i % cores.length] }),
        s('text', { x: margemEsquerda + escala(Math.max(0, Math.min(1, valor))) + 6, y: y + 13, 'font-size': 11.5 },
          item.valor === null || item.valor === undefined ? '—' : formato.metrica(item.valor)),
      );
    });
  });

  return h('figure', { style: 'margin:0' }, h('figcaption', { class: 'rotulo' }, titulo), svg);
}

export const CORES_SERIES = ['#1d4ed8', '#b45309', '#047857', '#7c3aed', '#be123c'];
