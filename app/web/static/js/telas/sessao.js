// O04 Avaliar a segmentação de uma imagem (M01):
// O04.1 Ver o resultado sobre a imagem · baixar a imagem (no modo escolhido) ou o vídeo segmentado.
import { api, enc, ErroApi } from '../api.js';
import { h, limpar, cabecalho, mensagem, legenda, icone } from '../ui.js';
import { Regiao, Visualizador } from '../visualizador.js';
import {
  configuracoesExecutadas, imagensComResultado, rotuloImagem, temMascara, urlImagem, urlMascara, urlSobreposicao,
} from './comum.js';

function lerPreferencia(chave, padrao) {
  try { return localStorage.getItem(chave) ?? padrao; } catch { return padrao; }
}
function gravarPreferencia(chave, valor) {
  try { localStorage.setItem(chave, valor); } catch { /* sem armazenamento: só não lembra */ }
}

export async function renderAtual(main, _p, _c, contexto) {
  let sessao;
  try {
    sessao = await api.get('/api/sessoes/atual');
  } catch (erro) {
    if (erro instanceof ErroApi && erro.status === 404) {
      limpar(main, cabecalho('Sessão atual'), mensagem('neutra',
        h('p', {}, 'Ainda não há sessão de segmentação.'),
        h('p', {}, h('a', { href: '#/segmentar' }, 'Envie as imagens do teste em Segmentar imagens'), '.')));
      return null;
    }
    throw erro;
  }

  const execucoes = Object.values(sessao.execucoes);
  const pendente = execucoes.some((e) => ['na fila', 'processando', 'falhou'].includes(e.estado) || Object.keys(e.falhas || {}).length)
    || sessao.videos.some((v) => v.estado !== 'concluído');
  contexto.navegar(pendente ? `#/sessao/${enc(sessao.id)}/processamento` : `#/sessao/${enc(sessao.id)}/imagem`);
  return null;
}

export async function render(main, { id }, consulta) {
  let sessao = await api.get(`/api/sessoes/${enc(id)}`);
  const executadas = configuracoesExecutadas(sessao);
  sessao.imagens = imagensComResultado(sessao);

  limpar(main, cabecalho('Avaliar a segmentação de cada imagem',
    `Ciclo de testes: ${sessao.ciclo} · ${sessao.imagens.length} imagens nesta sessão`,
    h('a', { href: `#/sessao/${enc(id)}/processamento` }, '← Acompanhar o processamento')));

  if (!executadas.length) {
    main.append(mensagem('neutra', h('p', {}, 'Ainda não há resultado nesta sessão.'),
      h('a', { href: `#/sessao/${enc(id)}/processamento` }, 'Acompanhar o processamento')));
    return null;
  }

  const estado = {
    imagem: consulta.get('nome') && sessao.imagens.some((i) => i.nome === consulta.get('nome')) ? consulta.get('nome') : sessao.imagens[0].nome,
    configuracao: executadas.some((c) => c.id === consulta.get('cfg')) ? consulta.get('cfg') : executadas[0].id,
    modo: lerPreferencia('modo-visualizacao', 'sobreposicao'),
    transparencia: Number(lerPreferencia('transparencia', '50')),
  };
  let visualizadores = [];
  const regiao = new Regiao();

  const lista = h('ul', { class: 'lista-imagens', 'aria-label': 'Imagens da sessão' });
  const resumo = h('p', { class: 'pequeno suave' });
  const area = h('div', {});

  main.append(h('div', { class: 'grade-lateral' },
    h('div', {}, h('h2', {}, 'Imagens'), resumo, lista),
    area));

  const indice = (nome) => sessao.imagens.findIndex((i) => i.nome === nome);
  const imagemAtual = () => sessao.imagens[indice(estado.imagem)];

  function desenharLista() {
    const videos = new Set(sessao.imagens.filter((i) => i.origem === 'quadro').map((i) => i.video)).size;
    const imagens = sessao.imagens.filter((i) => i.origem !== 'quadro').length;
    resumo.textContent = `${imagens} imagem(ns) · ${videos} vídeo(s)`;

    const itens = [];
    const videosListados = new Set();
    for (const imagem of sessao.imagens) {
      if (imagem.origem === 'quadro') {
        if (videosListados.has(imagem.video)) continue;
        videosListados.add(imagem.video);
        const quadros = sessao.imagens.filter((i) => i.video === imagem.video);
        const atual = imagemAtual()?.video === imagem.video;
        itens.push(h('li', {}, h('button', {
          type: 'button', 'aria-current': atual ? 'true' : null,
          onclick: () => escolherImagem(atual ? estado.imagem : quadros[0].nome),
        }, h('span', { class: 'nome-imagem' }, `Vídeo ${imagem.video}`),
        h('span', { class: 'pequeno suave' }, `${quadros.length} quadros`))));
        continue;
      }
      itens.push(h('li', {}, h('button', {
        type: 'button', 'aria-current': imagem.nome === estado.imagem ? 'true' : null,
        onclick: () => escolherImagem(imagem.nome),
      }, h('span', { class: 'nome-imagem' }, rotuloImagem(imagem)))));
    }
    limpar(lista, itens);
  }

  function escolherImagem(nome) {
    estado.imagem = nome;
    regiao.inteira();
    history.replaceState(null, '', `#/sessao/${enc(id)}/imagem?nome=${enc(nome)}&cfg=${enc(estado.configuracao)}`);
    desenharLista();
    desenharArea();
  }

  function criarVisualizadores(container) {
    visualizadores.forEach((v) => v.destruir());
    visualizadores = [];
    const imagem = imagemAtual();
    const comMascara = temMascara(sessao, estado.configuracao, imagem.nome);
    const nomeConfiguracao = sessao.configuracoes[estado.configuracao]?.nome || '';
    const semMascaraTexto = 'Sem máscara: a segmentação desta imagem falhou ou foi deixada de fora.';
    const base = {
      urlImagem: urlImagem(id, imagem.nome),
      urlMascara: comMascara ? urlMascara(id, estado.configuracao, imagem.nome) : null,
      regiao, transparencia: estado.transparencia, semMascaraTexto,
    };

    if (estado.modo === 'lado') {
      visualizadores = [
        new Visualizador({ ...base, titulo: 'Imagem original', modo: 'original' }),
        new Visualizador({ ...base, titulo: `Máscara · ${nomeConfiguracao}`, modo: 'mascara' }),
      ];
      container.className = 'grade-visualizadores colunas-2';
    } else {
      visualizadores = [new Visualizador({ ...base, titulo: `Sobreposição · ${nomeConfiguracao}`, modo: 'sobreposicao' })];
      container.className = 'grade-visualizadores';
    }
    if (!comMascara) visualizadores.forEach((v) => { v.semMascara = true; });
    limpar(container, visualizadores.map((v) => v.elemento));
  }

  function navegacaoDeQuadros(imagem) {
    if (imagem.origem !== 'quadro') return null;
    const quadros = sessao.imagens.filter((i) => i.video === imagem.video);
    const posicao = quadros.findIndex((q) => q.nome === imagem.nome);
    const barra = h('input', {
      type: 'range', min: '1', max: String(quadros.length), value: String(posicao + 1), id: 'barra-quadro',
      'aria-label': `Quadro do vídeo ${imagem.video}`, 'aria-valuetext': `Quadro ${posicao + 1} de ${quadros.length}`,
    });
    barra.addEventListener('change', () => escolherImagem(quadros[Number(barra.value) - 1].nome));
    barra.addEventListener('input', () => { saida.textContent = `Quadro ${barra.value} de ${quadros.length}`; });
    const saida = h('output', { for: 'barra-quadro' }, `Quadro ${posicao + 1} de ${quadros.length}`);
    const video = sessao.execucoes[estado.configuracao]?.videos?.[imagem.video];

    return h('div', { class: 'cartao' },
      h('div', { class: 'navegacao-quadros' },
        h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', disabled: posicao === 0, onclick: () => escolherImagem(quadros[posicao - 1].nome) }, '← Quadro anterior'),
        barra, saida,
        h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', disabled: posicao === quadros.length - 1, onclick: () => escolherImagem(quadros[posicao + 1].nome) }, 'Próximo quadro →')),
      h('p', { class: 'pequeno', style: 'margin:.5rem 0 0' }, video
        ? h('a', { href: `/api/sessoes/${enc(id)}/videos/${enc(estado.configuracao)}/${enc(imagem.video)}`, download: '' },
          `Baixar o vídeo com a sobreposição da ${sessao.configuracoes[estado.configuracao]?.nome} (MP4)`)
        : h('span', { class: 'suave' }, 'O vídeo com a sobreposição fica disponível quando todos os quadros forem segmentados.')));
  }

  function desenharArea() {
    const imagem = imagemAtual();
    const container = h('div', {});

    const seletorConfiguracao = executadas.length > 1 ? h('label', { class: 'linha' }, h('span', { class: 'rotulo' }, 'Configuração:'),
      h('select', {
        onchange: (e) => { estado.configuracao = e.target.value; escolherImagem(estado.imagem); },
      }, executadas.map((c) => h('option', { value: c.id, selected: c.id === estado.configuracao }, c.nome)))) : h('span', {}, h('span', { class: 'rotulo' }, 'Configuração: '), executadas[0].nome);

    const alternancia = h('div', { class: 'grupo-alternancia', role: 'group', 'aria-label': 'Como mostrar' },
      [['sobreposicao', 'Sobreposição'], ['lado', 'Imagem original e máscara']].map(([valor, rotulo]) => h('button', {
        type: 'button', 'aria-pressed': String(estado.modo === valor),
        onclick: () => { estado.modo = valor; gravarPreferencia('modo-visualizacao', valor); desenharArea(); },
      }, rotulo)));

    // Um só botão de download (só o ícone), ao lado da alternância: baixa a imagem no modo que está sendo mostrado.
    // O aria-label e o title dizem o que será baixado para quem usa leitor de tela ou passa o mouse.
    const comMascara = temMascara(sessao, estado.configuracao, imagem.nome);
    const sobreposicao = estado.modo === 'sobreposicao';
    const descricaoBaixar = !comMascara ? 'Sem máscara desta imagem nesta configuração'
      : sobreposicao ? 'Baixar a sobreposição (PNG)' : 'Baixar a máscara (PNG)';
    const botaoBaixar = comMascara
      ? h('a', {
        class: 'botao botao-secundario botao-pequeno botao-icone', download: '', 'aria-label': descricaoBaixar, title: descricaoBaixar,
        href: sobreposicao ? urlSobreposicao(id, estado.configuracao, imagem.nome) : `${urlMascara(id, estado.configuracao, imagem.nome)}?baixar=true`,
      }, icone('baixar'))
      : h('button', {
        type: 'button', class: 'botao botao-secundario botao-pequeno botao-icone', disabled: true, 'aria-label': descricaoBaixar, title: descricaoBaixar,
      }, icone('baixar'));

    const barraTransparencia = h('input', {
      type: 'range', min: '0', max: '100', step: '5', value: String(estado.transparencia), id: 'transparencia',
      'aria-valuetext': `${estado.transparencia}%`,
    });
    const saidaTransparencia = h('output', { for: 'transparencia' }, `${estado.transparencia}%`);
    barraTransparencia.addEventListener('input', () => {
      estado.transparencia = Number(barraTransparencia.value);
      saidaTransparencia.textContent = `${estado.transparencia}%`;
      barraTransparencia.setAttribute('aria-valuetext', `${estado.transparencia}%`);
      gravarPreferencia('transparencia', String(estado.transparencia));
      visualizadores.forEach((v) => v.definir({ transparencia: estado.transparencia }));
    });

    limpar(area,
      h('h2', { tabindex: '-1' }, rotuloImagem(imagem)),
      h('div', { class: 'controles-visualizacao' },
        seletorConfiguracao,
        h('span', { class: 'linha' }, alternancia, botaoBaixar),
        estado.modo === 'sobreposicao' ? h('span', { class: 'linha' },
          h('label', { for: 'transparencia', class: 'rotulo' }, 'Transparência'), barraTransparencia, saidaTransparencia) : null),
      legenda(estado.modo === 'sobreposicao' ? 'sobreposicao' : 'mascara'),
      navegacaoDeQuadros(imagem),
      container);

    criarVisualizadores(container);
  }

  desenharLista();
  desenharArea();

  return { sair: () => visualizadores.forEach((v) => v.destruir()) };
}
