// Visualização da imagem original, da máscara e da sobreposição, com região ampliada compartilhada.
// Na comparação (O05.2) todos os visualizadores usam a mesma Regiao: ampliar um amplia todos.
import { h } from './ui.js';

const TRILHA = [255, 176, 0];          // --trilha
const FORA_DA_TRILHA = [43, 58, 85];   // --fora-da-trilha
const CONTORNO = [255, 255, 255];
const ZOOM_MAXIMO = 12;

const cacheMascaras = new Map();

export class Regiao {
  constructor() {
    this.zoom = 1;
    this.cx = 0.5;
    this.cy = 0.5;
    this.ouvintes = new Set();
  }

  definir(zoom, cx, cy) {
    this.zoom = Math.min(ZOOM_MAXIMO, Math.max(1, zoom));
    const metade = 0.5 / this.zoom;
    this.cx = Math.min(1 - metade, Math.max(metade, cx));
    this.cy = Math.min(1 - metade, Math.max(metade, cy));
    this.ouvintes.forEach((ouvinte) => ouvinte());
  }

  ampliar(fator, cx = this.cx, cy = this.cy) {
    // Mantém o ponto (cx, cy) no mesmo lugar da tela ao ampliar ao redor dele
    const novoZoom = Math.min(ZOOM_MAXIMO, Math.max(1, this.zoom * fator));
    const escala = this.zoom / novoZoom;
    this.definir(novoZoom, cx + (this.cx - cx) * escala, cy + (this.cy - cy) * escala);
  }

  mover(dx, dy) { this.definir(this.zoom, this.cx + dx, this.cy + dy); }
  inteira() { this.definir(1, 0.5, 0.5); }
  ouvir(funcao) { this.ouvintes.add(funcao); return () => this.ouvintes.delete(funcao); }
  get texto() { return this.zoom <= 1.001 ? 'imagem inteira' : `ampliada ${this.zoom.toFixed(1).replace('.', ',')}×`; }
}

function carregarImagem(url) {
  return new Promise((resolver, rejeitar) => {
    const imagem = new Image();
    imagem.onload = () => resolver(imagem);
    imagem.onerror = () => rejeitar(new Error('imagem indisponível'));
    imagem.src = url;
  });
}

// A máscara chega em tons de cinza (0 = Fora da trilha, 255 = Trilha) e vira duas camadas coloridas
async function camadasDaMascara(url) {
  if (cacheMascaras.has(url)) return cacheMascaras.get(url);

  const promessa = carregarImagem(url).then((imagem) => {
    const largura = imagem.naturalWidth;
    const altura = imagem.naturalHeight;
    const leitura = document.createElement('canvas');
    leitura.width = largura;
    leitura.height = altura;
    const contexto = leitura.getContext('2d', { willReadFrequently: true });
    contexto.drawImage(imagem, 0, 0);
    const dados = contexto.getImageData(0, 0, largura, altura).data;

    const trilha = new Uint8Array(largura * altura);
    for (let i = 0; i < trilha.length; i++) trilha[i] = dados[i * 4] > 127 ? 1 : 0;

    const mascara = new ImageData(largura, altura);
    const pintura = new ImageData(largura, altura);
    const contorno = new ImageData(largura, altura);

    for (let y = 0; y < altura; y++) {
      for (let x = 0; x < largura; x++) {
        const i = y * largura + x;
        const p = i * 4;
        const cor = trilha[i] ? TRILHA : FORA_DA_TRILHA;
        mascara.data[p] = cor[0]; mascara.data[p + 1] = cor[1]; mascara.data[p + 2] = cor[2]; mascara.data[p + 3] = 255;

        if (!trilha[i]) continue;
        pintura.data[p] = TRILHA[0]; pintura.data[p + 1] = TRILHA[1]; pintura.data[p + 2] = TRILHA[2]; pintura.data[p + 3] = 255;

        // Contorno da trilha: a informação não depende só da cor (WCAG 1.4.1)
        const borda = x === 0 || y === 0 || x === largura - 1 || y === altura - 1
          || !trilha[i - 1] || !trilha[i + 1] || !trilha[i - largura] || !trilha[i + largura];
        if (borda) {
          contorno.data[p] = CONTORNO[0]; contorno.data[p + 1] = CONTORNO[1]; contorno.data[p + 2] = CONTORNO[2]; contorno.data[p + 3] = 255;
        }
      }
    }

    const emCanvas = (imageData) => {
      const canvas = document.createElement('canvas');
      canvas.width = largura;
      canvas.height = altura;
      canvas.getContext('2d').putImageData(imageData, 0, 0);
      return canvas;
    };

    let pixelsTrilha = 0;
    for (let i = 0; i < trilha.length; i++) pixelsTrilha += trilha[i];

    return {
      mascara: emCanvas(mascara),
      pintura: emCanvas(pintura),
      contorno: emCanvas(contorno),
      largura,
      altura,
      fracaoTrilha: pixelsTrilha / trilha.length,
    };
  });

  cacheMascaras.set(url, promessa);
  promessa.catch(() => cacheMascaras.delete(url));
  return promessa;
}

export function limparCacheMascaras() { cacheMascaras.clear(); }

/**
 * Um quadro de visualização.
 * opcoes: { titulo, urlImagem, urlMascara (ou null), modo: 'original'|'mascara'|'sobreposicao',
 *           transparencia (0-100), regiao (Regiao compartilhada), semMascaraTexto }
 */
export class Visualizador {
  constructor(opcoes) {
    this.opcoes = { modo: 'sobreposicao', transparencia: 50, ...opcoes };
    this.regiao = opcoes.regiao || new Regiao();
    this.canvas = h('canvas', { tabindex: '0', role: 'img' });
    this.quadro = h('div', { class: 'visualizador-quadro' }, this.canvas);
    this.elemento = h('figure', { class: 'visualizador', style: 'margin:0' },
      h('figcaption', { class: 'visualizador-titulo' }, h('span', {}, opcoes.titulo || ''), h('span', { class: 'suave pequeno', 'data-regiao': '' })),
      this.quadro);

    this.cancelar = this.regiao.ouvir(() => this.desenhar());
    this.ligarInteracao();
    this.carregar();
  }

  async carregar() {
    try {
      this.imagem = await carregarImagem(this.opcoes.urlImagem);
    } catch {
      this.mostrarVazio('Não foi possível abrir a imagem original.');
      return;
    }

    if (this.opcoes.urlMascara) {
      try {
        this.camadas = await camadasDaMascara(this.opcoes.urlMascara);
      } catch {
        this.camadas = null;
        this.semMascara = true;
      }
    }
    this.desenhar();
  }

  mostrarVazio(texto) {
    this.quadro.replaceChildren(h('div', { class: 'visualizador-vazio' }, texto));
  }

  definir(mudancas) {
    Object.assign(this.opcoes, mudancas);
    this.desenhar();
  }

  descricao() {
    const { modo, transparencia, titulo } = this.opcoes;
    const partes = [titulo];
    if (modo === 'original') partes.push('imagem original');
    else if (this.semMascara) partes.push('imagem original; não há máscara para esta imagem');
    else if (modo === 'mascara') partes.push('máscara: Trilha em amarelo, Fora da trilha em azul escuro');
    else partes.push(`sobreposição com transparência de ${transparencia}%: Trilha pintada de amarelo com contorno branco`);
    if (this.camadas && modo !== 'original') partes.push(`cerca de ${Math.round(this.camadas.fracaoTrilha * 100)}% da imagem marcada como Trilha`);
    partes.push(this.regiao.texto);
    return partes.filter(Boolean).join('. ');
  }

  desenhar() {
    if (!this.imagem) return;
    const largura = this.imagem.naturalWidth;
    const altura = this.imagem.naturalHeight;

    // Resolução do canvas acompanha o tamanho exibido (nítido também ampliado)
    const exibida = Math.max(200, Math.round(this.quadro.clientWidth || 480));
    const escalaTela = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(exibida * escalaTela);
    this.canvas.height = Math.round((exibida * altura / largura) * escalaTela);

    const contexto = this.canvas.getContext('2d');
    const { zoom, cx, cy } = this.regiao;
    const sw = largura / zoom;
    const sh = altura / zoom;
    const sx = cx * largura - sw / 2;
    const sy = cy * altura - sh / 2;
    const destino = [0, 0, this.canvas.width, this.canvas.height];

    contexto.imageSmoothingEnabled = true;
    contexto.globalAlpha = 1;

    const { modo, transparencia } = this.opcoes;
    const camadas = this.camadas;
    const escalaMascara = camadas ? camadas.largura / largura : 1;
    const origemMascara = [sx * escalaMascara, sy * escalaMascara, sw * escalaMascara, sh * escalaMascara];

    if (modo === 'mascara' && camadas) {
      contexto.imageSmoothingEnabled = false;
      contexto.drawImage(camadas.mascara, ...origemMascara, ...destino);
      contexto.drawImage(camadas.contorno, ...origemMascara, ...destino);
    } else {
      contexto.drawImage(this.imagem, sx, sy, sw, sh, ...destino);
      if (modo === 'sobreposicao' && camadas && transparencia > 0) {
        contexto.imageSmoothingEnabled = false;
        contexto.globalAlpha = transparencia / 100;
        contexto.drawImage(camadas.pintura, ...origemMascara, ...destino);
        contexto.globalAlpha = 1;
        contexto.drawImage(camadas.contorno, ...origemMascara, ...destino);
      }
    }

    if (this.semMascara && modo !== 'original') {
      contexto.fillStyle = 'rgba(17,21,28,.75)';
      contexto.fillRect(0, 0, this.canvas.width, 34 * escalaTela);
      contexto.fillStyle = '#fff';
      contexto.font = `${14 * escalaTela}px system-ui, sans-serif`;
      contexto.fillText(this.opcoes.semMascaraTexto || 'Sem máscara para esta imagem', 10 * escalaTela, 22 * escalaTela);
    }

    this.canvas.setAttribute('aria-label', this.descricao());
    const rotulo = this.elemento.querySelector('[data-regiao]');
    if (rotulo) rotulo.textContent = this.regiao.texto;
  }

  ligarInteracao() {
    let arrasto = null;

    this.canvas.addEventListener('wheel', (evento) => {
      evento.preventDefault();
      const caixa = this.canvas.getBoundingClientRect();
      const { zoom, cx, cy } = this.regiao;
      const px = cx + ((evento.clientX - caixa.left) / caixa.width - 0.5) / zoom;
      const py = cy + ((evento.clientY - caixa.top) / caixa.height - 0.5) / zoom;
      this.regiao.ampliar(evento.deltaY < 0 ? 1.25 : 0.8, px, py);
    }, { passive: false });

    this.canvas.addEventListener('pointerdown', (evento) => {
      arrasto = { x: evento.clientX, y: evento.clientY };
      this.canvas.setPointerCapture(evento.pointerId);
    });
    this.canvas.addEventListener('pointermove', (evento) => {
      if (!arrasto) return;
      const caixa = this.canvas.getBoundingClientRect();
      const dx = (evento.clientX - arrasto.x) / caixa.width / this.regiao.zoom;
      const dy = (evento.clientY - arrasto.y) / caixa.height / this.regiao.zoom;
      arrasto = { x: evento.clientX, y: evento.clientY };
      this.regiao.mover(-dx, -dy);
    });
    const soltar = () => { arrasto = null; };
    this.canvas.addEventListener('pointerup', soltar);
    this.canvas.addEventListener('pointercancel', soltar);

    // Teclado: + e − ampliam, setas movem a região, 0 volta à imagem inteira
    this.canvas.addEventListener('keydown', (evento) => {
      const passo = 0.1 / this.regiao.zoom;
      const acoes = {
        '+': () => this.regiao.ampliar(1.25), '=': () => this.regiao.ampliar(1.25),
        '-': () => this.regiao.ampliar(0.8), '0': () => this.regiao.inteira(),
        ArrowLeft: () => this.regiao.mover(-passo, 0), ArrowRight: () => this.regiao.mover(passo, 0),
        ArrowUp: () => this.regiao.mover(0, -passo), ArrowDown: () => this.regiao.mover(0, passo),
      };
      if (acoes[evento.key]) {
        evento.preventDefault();
        acoes[evento.key]();
      }
    });

    this.observador = new ResizeObserver(() => this.desenhar());
    this.observador.observe(this.quadro);
  }

  destruir() {
    this.cancelar();
    this.observador?.disconnect();
  }
}

// Botões de ampliar/reduzir para quem não usa a roda do mouse
export function controlesDeRegiao(regiao) {
  return h('div', { class: 'linha', role: 'group', 'aria-label': 'Região ampliada' },
    h('span', { class: 'rotulo' }, 'Região ampliada:'),
    h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', onclick: () => regiao.ampliar(1.5) }, 'Ampliar'),
    h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', onclick: () => regiao.ampliar(1 / 1.5) }, 'Reduzir'),
    h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', onclick: () => regiao.inteira() }, 'Imagem inteira'),
    h('span', { class: 'suave pequeno' }, 'Também: roda do mouse, arrastar, ou + − 0 e setas com a imagem em foco.'));
}
