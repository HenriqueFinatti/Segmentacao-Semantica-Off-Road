// O04 Avaliar a segmentação de uma imagem (M01):
// O04.1 Ver o resultado sobre a imagem · O04.2 Conferir se há métricas · O04.3 Registrar a avaliação da imagem.
import { api, enc, ErroApi } from '../api.js';
import { h, limpar, cabecalho, mensagem, legenda, termo, anunciar, falhaDaApi } from '../ui.js';
import { Regiao, Visualizador, controlesDeRegiao } from '../visualizador.js';
import {
  configuracoesExecutadas, imagensComResultado, marcadorAvaliacao, rotuloImagem, temMascara, textoAvaliacao, urlImagem, urlMascara,
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
    const avaliadas = Object.keys(sessao.avaliacoes).length;
    const duvidosas = Object.values(sessao.avaliacoes).filter((a) => a.avaliacao === 'duvidosa').length;
    resumo.textContent = `${avaliadas} de ${sessao.imagens.length} avaliadas · ${duvidosas} duvidosa(s)`;

    const itens = [];
    const videosListados = new Set();
    for (const imagem of sessao.imagens) {
      if (imagem.origem === 'quadro') {
        if (videosListados.has(imagem.video)) continue;
        videosListados.add(imagem.video);
        const quadros = sessao.imagens.filter((i) => i.video === imagem.video);
        const avaliados = quadros.filter((q) => sessao.avaliacoes[q.nome]).length;
        const atual = imagemAtual()?.video === imagem.video;
        itens.push(h('li', {}, h('button', {
          type: 'button', 'aria-current': atual ? 'true' : null,
          onclick: () => escolherImagem(atual ? estado.imagem : quadros[0].nome),
        }, h('span', { class: 'nome-imagem' }, `Vídeo ${imagem.video}`),
        h('span', { class: 'pequeno suave' }, `${quadros.length} quadros · ${avaliados} avaliado(s)`))));
        continue;
      }
      itens.push(h('li', {}, h('button', {
        type: 'button', 'aria-current': imagem.nome === estado.imagem ? 'true' : null,
        onclick: () => escolherImagem(imagem.nome),
      }, h('span', { class: 'nome-imagem' }, rotuloImagem(imagem)), marcadorAvaliacao(sessao.avaliacoes[imagem.nome]))));
    }
    limpar(lista, itens);
  }

  function escolherImagem(nome, focar = false) {
    estado.imagem = nome;
    regiao.inteira();
    history.replaceState(null, '', `#/sessao/${enc(id)}/imagem?nome=${enc(nome)}&cfg=${enc(estado.configuracao)}`);
    desenharLista();
    desenharArea();
    if (focar) area.querySelector('h2')?.focus();
  }

  function proximaImagem() {
    const atual = indice(estado.imagem);
    const ordem = [...sessao.imagens.slice(atual + 1), ...sessao.imagens.slice(0, atual + 1)];
    const proxima = ordem.find((i) => !sessao.avaliacoes[i.nome]) || sessao.imagens[(atual + 1) % sessao.imagens.length];
    escolherImagem(proxima.nome, true);
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
    const execucao = sessao.execucoes[estado.configuracao] || {};
    const video = execucao.videos?.[imagem.video];

    return h('div', { class: 'cartao' },
      h('div', { class: 'navegacao-quadros' },
        h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', disabled: posicao === 0, onclick: () => escolherImagem(quadros[posicao - 1].nome) }, '← Quadro anterior'),
        barra, saida,
        h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', disabled: posicao === quadros.length - 1, onclick: () => escolherImagem(quadros[posicao + 1].nome) }, 'Próximo quadro →')),
      video ? h('p', { class: 'pequeno', style: 'margin:.5rem 0 0' },
        h('a', { href: `/api/sessoes/${enc(id)}/videos/${enc(estado.configuracao)}/${enc(imagem.video)}`, download: '' },
          `Baixar o vídeo com a sobreposição da ${sessao.configuracoes[estado.configuracao]?.nome} (MP4)`)) : null);
  }

  function painelMetricas() {
    // O04.2: imagens de campo não têm anotação de referência; nunca há IoU ou acurácia por imagem (prevenção passiva)
    return h('section', { class: 'cartao', 'aria-labelledby': 'titulo-metricas' },
      h('h2', { id: 'titulo-metricas' }, 'Métricas desta imagem'),
      mensagem('neutra',
        h('p', {}, h('strong', {}, 'Sem métricas: avaliação visual. '), 'As métricas estão no ',
          h('a', { href: '#/desempenho' }, 'desempenho consolidado'), '.'),
        h('p', { class: 'pequeno' }, 'Esta imagem de campo não tem ', termo('anotação de referência', 'anotacao_de_referencia'),
          ', por isso não há ', termo('IoU', 'iou'), ' nem ', termo('acurácia', 'acuracia'), ' para ela. Compare a máscara com a imagem original, com a ',
          termo('sobreposição', 'sobreposicao'), ' e a ', termo('região ampliada', 'regiao_ampliada'), '.')));
  }

  function formularioAvaliacao() {
    const imagem = imagemAtual();
    const registrada = sessao.avaliacoes[imagem.nome];
    const confirmacao = h('p', { class: 'pequeno', 'aria-live': 'polite' },
      registrada ? h('span', {}, 'Avaliação registrada: ', h('strong', {}, textoAvaliacao(registrada)), '.') : 'Esta imagem ainda não tem avaliação.');

    const radio = (nome, valor, rotulo, marcado, desabilitado = false) => h('label', { class: `opcao ${desabilitado ? 'desabilitada' : ''}` },
      h('input', { type: 'radio', name: nome, value: valor, checked: marcado, disabled: desabilitado }), rotulo);

    const duvidosa = registrada?.avaliacao === 'duvidosa';
    const origem = h('fieldset', { 'data-campo': 'origem_problema' },
      h('legend', {}, termo('Origem do problema', 'origem_problema'), ' (só para duvidosas)'),
      radio('origem', 'imagem (captura)', 'Problema na imagem (captura)', registrada?.origem_problema === 'imagem (captura)', !duvidosa),
      radio('origem', 'modelo', 'Problema no modelo', registrada?.origem_problema === 'modelo', !duvidosa));

    const formulario = h('form', { class: 'cartao', 'aria-labelledby': 'titulo-avaliacao' },
      h('h2', { id: 'titulo-avaliacao' }, 'Registrar a ', termo('avaliação da imagem', 'avaliacao_imagem')),
      h('fieldset', { 'data-campo': 'avaliacao' },
        h('legend', {}, 'A segmentação desta imagem está:'),
        radio('avaliacao', 'correta', 'Correta', registrada?.avaliacao === 'correta'),
        radio('avaliacao', 'duvidosa', 'Duvidosa', duvidosa)),
      origem,
      h('div', { class: 'linha' },
        h('button', { type: 'submit', class: 'botao' }, 'Registrar avaliação'),
        h('button', { type: 'button', class: 'botao botao-secundario', onclick: proximaImagem }, 'Próxima imagem')),
      confirmacao);

    // Prevenção ativa: a origem do problema só pode ser informada para imagens duvidosas
    formulario.addEventListener('change', (evento) => {
      if (evento.target.name !== 'avaliacao') return;
      const habilitar = evento.target.value === 'duvidosa';
      origem.querySelectorAll('input').forEach((entrada) => {
        entrada.disabled = !habilitar;
        entrada.closest('.opcao').classList.toggle('desabilitada', !habilitar);
        if (!habilitar) entrada.checked = false;
      });
    });

    formulario.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      const avaliacao = formulario.querySelector('input[name="avaliacao"]:checked')?.value;
      const origemProblema = formulario.querySelector('input[name="origem"]:checked')?.value || null;
      if (!avaliacao) {
        confirmacao.textContent = 'Marque a imagem como correta ou duvidosa.';
        formulario.querySelector('input[name="avaliacao"]').focus();
        return;
      }
      try {
        const registro = await api.put(`/api/sessoes/${enc(id)}/avaliacoes/${enc(imagem.nome)}`,
          { avaliacao, origem_problema: origemProblema, configuracao: estado.configuracao });
        sessao.avaliacoes[imagem.nome] = registro;
        desenharLista();
        limpar(confirmacao, h('span', {}, h('strong', {}, 'Registrado: '), `${textoAvaliacao(registro)}.`));
        anunciar(`Registrado: ${textoAvaliacao(registro)}.`);
        formulario.querySelector('.botao-secundario').focus();
        desenharAcoes();
      } catch (erro) {
        await falhaDaApi(erro, 'Não foi possível registrar a avaliação');
      }
    });
    return formulario;
  }

  const acoes = h('div', { class: 'cartao' });
  function desenharAcoes() {
    const duvidosas = Object.values(sessao.avaliacoes).filter((a) => a.avaliacao === 'duvidosa').length;
    limpar(acoes,
      h('h2', {}, 'Depois de avaliar'),
      h('div', { class: 'linha' },
        h('a', {
          class: `botao botao-secundario`, href: duvidosas ? `#/sessao/${enc(id)}/escolher-comparacao` : null,
          'aria-disabled': duvidosas ? null : 'true', role: 'link',
        }, `Comparar as duvidosas (${duvidosas})`),
        executadas.length > 1 ? h('a', { class: 'botao botao-secundario', href: `#/sessao/${enc(id)}/comparar?imagem=${enc(estado.imagem)}` }, 'Comparar na mesma imagem e região') : null,
        h('a', { class: 'botao', href: `#/conclusao/nova?tipo=${enc('validação')}&sessao=${enc(id)}` }, 'Registrar a conclusão')),
      !duvidosas ? h('p', { class: 'pequeno suave', style: 'margin-top:.4rem' }, 'Comparar fica disponível quando houver imagens duvidosas.') : null);
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
      h('h2', { tabindex: '-1' }, rotuloImagem(imagem), ' ', marcadorAvaliacao(sessao.avaliacoes[imagem.nome])),
      h('div', { class: 'controles-visualizacao' },
        seletorConfiguracao,
        alternancia,
        estado.modo === 'sobreposicao' ? h('span', { class: 'linha' },
          h('label', { for: 'transparencia', class: 'rotulo' }, termo('Transparência', 'transparencia')), barraTransparencia, saidaTransparencia) : null,
        controlesDeRegiao(regiao)),
      legenda(estado.modo === 'sobreposicao' ? 'sobreposicao' : 'mascara'),
      navegacaoDeQuadros(imagem),
      container,
      h('div', { style: 'margin:.75rem 0' }, painelMetricas()),
      formularioAvaliacao(),
      acoes);

    criarVisualizadores(container);
    desenharAcoes();
  }

  desenharLista();
  desenharArea();

  return { sair: () => visualizadores.forEach((v) => v.destruir()) };
}
