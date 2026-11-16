// O05 Comparar configurações sobre a mesma entrada:
// O05.1 Escolher as configurações a comparar · O05.2 Comparar na mesma imagem e região (cena reusada pelo M01 e pelo M03).
import { api, enc } from '../api.js';
import { h, limpar, cabecalho, mensagem, legenda, termo, falhaDaApi } from '../ui.js';
import { Regiao, Visualizador, controlesDeRegiao } from '../visualizador.js';
import {
  configuracoesExecutadas, imagensComResultado, marcadorAvaliacao, rotuloImagem, seletorDeConfiguracoes, temMascara, textoAvaliacao, urlImagem,
  urlMascara,
} from './comum.js';

export async function renderEscolher(main, { id }, _consulta, contexto) {
  const [sessao, configuracoes] = await Promise.all([api.get(`/api/sessoes/${enc(id)}`), api.get('/api/configuracoes')]);
  sessao.imagens = imagensComResultado(sessao);
  const disponiveis = configuracoes.filter((c) => c.disponivel);
  const duvidosas = sessao.imagens.filter((i) => sessao.avaliacoes[i.nome]?.avaliacao === 'duvidosa');
  const outras = sessao.imagens.filter((i) => !duvidosas.includes(i));

  limpar(main, cabecalho('Escolher as configurações a comparar',
    'Escolha a outra configuração e as imagens. A comparação usa as mesmas imagens desta sessão.',
    h('a', { href: `#/sessao/${enc(id)}/imagem` }, '← Avaliar as imagens')));

  const jaExecutadaEm = (configuracao, nomes) => nomes.every((nome) => temMascara(sessao, configuracao.id, nome));
  const seletor = seletorDeConfiguracoes(disponiveis, {
    nome: 'comparar',
    rotulo: 'Configurações disponíveis',
    extras: (configuracao) => (jaExecutadaEm(configuracao, duvidosas.map((d) => d.nome))
      ? h('span', { class: 'pequeno', style: 'display:block;color:var(--ok);font-weight:600' }, '✓ Já executada nestas imagens') : null),
  });

  const caixaImagem = (imagem, marcada) => h('label', { class: 'opcao' },
    h('input', { type: 'checkbox', name: 'imagens', value: imagem.nome, checked: marcada }),
    h('span', {}, rotuloImagem(imagem), ' ', marcadorAvaliacao(sessao.avaliacoes[imagem.nome])));

  const formulario = h('form', { novalidate: true },
    h('div', { class: 'grade-2' },
      h('div', { class: 'cartao' },
        h('h2', {}, 'Imagens'),
        duvidosas.length ? h('fieldset', { 'data-campo': 'imagens' }, h('legend', {}, `Imagens duvidosas (${duvidosas.length})`), duvidosas.map((i) => caixaImagem(i, true)))
          : mensagem('neutra', h('p', {}, 'Nenhuma imagem está marcada como duvidosa. Escolha as imagens abaixo.')),
        outras.length ? h('details', {}, h('summary', {}, `Outras imagens da sessão (${outras.length})`), outras.map((i) => caixaImagem(i, false))) : null),
      h('div', { class: 'cartao' },
        h('h2', {}, 'Configurações'),
        h('p', { class: 'pequeno suave' }, 'Cada configuração mostra a descrição e as métricas no conjunto de teste.'),
        h('div', { 'data-campo': 'configuracoes' }, seletor.elemento))),
    h('p', { class: 'erro-campo', role: 'alert', id: 'erro-comparar' }),
    h('div', { class: 'linha' }, h('button', { type: 'submit', class: 'botao' }, 'Executar nas imagens escolhidas')));
  main.append(formulario);

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const aviso = formulario.querySelector('#erro-comparar');
    const imagens = [...formulario.querySelectorAll('input[name="imagens"]:checked')].map((e) => e.value);
    const escolhidas = seletor.valores();
    if (!imagens.length) { aviso.textContent = 'Escolha pelo menos uma imagem.'; return; }
    if (!escolhidas.length) { aviso.textContent = 'Escolha pelo menos uma configuração.'; return; }
    aviso.textContent = '';

    const executar = escolhidas.filter((cid) => !jaExecutadaEm({ id: cid }, imagens));
    const comparadas = [...new Set([...configuracoesExecutadas(sessao).map((c) => c.id), ...escolhidas])];
    const consulta = `configuracoes=${enc(comparadas.join(','))}&imagens=${enc(imagens.join(','))}`;

    if (!executar.length) {
      contexto.navegar(`#/sessao/${enc(id)}/comparar?${consulta}`);
      return;
    }
    try {
      await api.post(`/api/sessoes/${enc(id)}/executar`, { configuracoes: executar, imagens, comparacao: true });
      contexto.navegar(`#/sessao/${enc(id)}/processamento?depois=comparar`);
    } catch (erro) {
      await falhaDaApi(erro, 'Não foi possível executar');
    }
  });
}

export async function renderComparar(main, { id }, consulta) {
  const sessao = await api.get(`/api/sessoes/${enc(id)}`);
  sessao.imagens = imagensComResultado(sessao);
  const executadas = configuracoesExecutadas(sessao);
  const pedidas = (consulta.get('configuracoes') || '').split(',').filter(Boolean);
  const base = pedidas.length ? pedidas : (sessao.comparacao?.configuracoes || executadas.map((c) => c.id));
  const configuracoes = executadas.filter((c) => base.includes(c.id));
  const listaImagens = (consulta.get('imagens') || '').split(',').filter(Boolean);
  const imagens = (listaImagens.length ? listaImagens : (sessao.comparacao?.imagens || sessao.imagens.map((i) => i.nome)))
    .map((nome) => sessao.imagens.find((i) => i.nome === nome)).filter(Boolean);

  limpar(main, cabecalho('Comparar na mesma imagem e região',
    `Ciclo de testes: ${sessao.ciclo}. A mesma região ampliada vale para todas as configurações.`,
    h('a', { href: `#/sessao/${enc(id)}/imagem` }, '← Avaliar as imagens')));

  if (configuracoes.length < 2 || !imagens.length) {
    main.append(mensagem('neutra', h('p', {}, 'Para comparar, execute pelo menos duas configurações nas mesmas imagens.'),
      h('a', { href: `#/sessao/${enc(id)}/escolher-comparacao` }, 'Escolher as configurações a comparar')));
    return null;
  }

  const estado = {
    imagem: imagens.some((i) => i.nome === consulta.get('imagem')) ? consulta.get('imagem') : imagens[0].nome,
    modo: 'sobreposicao',
    transparencia: 50,
  };
  const regiao = new Regiao();
  let visualizadores = [];
  const area = h('div', {});
  main.append(area);

  function desenhar() {
    visualizadores.forEach((v) => v.destruir());
    const posicao = imagens.findIndex((i) => i.nome === estado.imagem);
    const imagem = imagens[posicao];
    const avaliacao = sessao.avaliacoes[imagem.nome];
    const urlBase = urlImagem(id, imagem.nome);

    visualizadores = [
      new Visualizador({ titulo: 'Imagem original', urlImagem: urlBase, modo: 'original', regiao }),
      ...configuracoes.map((c) => {
        const comMascara = temMascara(sessao, c.id, imagem.nome);
        const visualizador = new Visualizador({
          titulo: c.nome, urlImagem: urlBase, urlMascara: comMascara ? urlMascara(id, c.id, imagem.nome) : null,
          modo: estado.modo, transparencia: estado.transparencia, regiao,
          semMascaraTexto: 'Esta configuração não tem resultado para esta imagem.',
        });
        if (!comMascara) visualizador.semMascara = true;
        return visualizador;
      }),
    ];

    const seletorImagem = h('select', {
      id: 'imagem-comparada',
      onchange: (e) => { estado.imagem = e.target.value; regiao.inteira(); desenhar(); },
    }, imagens.map((i) => h('option', { value: i.nome, selected: i.nome === estado.imagem }, rotuloImagem(i))));

    const barra = h('input', { type: 'range', min: '0', max: '100', step: '5', value: String(estado.transparencia), id: 'transparencia-comparacao' });
    const saida = h('output', { for: 'transparencia-comparacao' }, `${estado.transparencia}%`);
    barra.addEventListener('input', () => {
      estado.transparencia = Number(barra.value);
      saida.textContent = `${estado.transparencia}%`;
      visualizadores.slice(1).forEach((v) => v.definir({ transparencia: estado.transparencia }));
    });

    const colunas = Math.min(3, visualizadores.length);
    limpar(area,
      h('div', { class: 'controles-visualizacao' },
        h('span', { class: 'linha' }, h('label', { for: 'imagem-comparada', class: 'rotulo' }, 'Imagem:'), seletorImagem,
          h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', disabled: posicao === 0,
            onclick: () => { estado.imagem = imagens[posicao - 1].nome; regiao.inteira(); desenhar(); } }, '← Anterior'),
          h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', disabled: posicao === imagens.length - 1,
            onclick: () => { estado.imagem = imagens[posicao + 1].nome; regiao.inteira(); desenhar(); } }, 'Próxima →')),
        h('div', { class: 'grupo-alternancia', role: 'group', 'aria-label': 'Como mostrar cada configuração' },
          [['sobreposicao', 'Sobreposição'], ['mascara', 'Máscara']].map(([valor, rotulo]) => h('button', {
            type: 'button', 'aria-pressed': String(estado.modo === valor),
            onclick: () => { estado.modo = valor; desenhar(); },
          }, rotulo))),
        estado.modo === 'sobreposicao' ? h('span', { class: 'linha' },
          h('label', { for: 'transparencia-comparacao', class: 'rotulo' }, termo('Transparência', 'transparencia')), barra, saida) : null,
        controlesDeRegiao(regiao)),
      legenda(estado.modo === 'sobreposicao' ? 'sobreposicao' : 'mascara'),
      h('div', { class: `grade-visualizadores colunas-${colunas}`, style: 'margin-top:.5rem' }, visualizadores.map((v) => v.elemento)),
      h('div', { class: 'cartao', style: 'margin-top:1rem' },
        h('p', {}, h('strong', {}, 'Avaliação registrada desta imagem: '), textoAvaliacao(avaliacao), '.'),
        h('p', { class: 'pequeno suave' }, 'Estas imagens não têm anotação de referência: a comparação aqui é visual. As métricas valem só para o conjunto de teste.'),
        h('div', { class: 'linha' },
          h('a', { class: 'botao', href: `#/sessao/${enc(id)}/imagem?nome=${enc(imagem.nome)}` }, 'Voltar à avaliação'),
          h('a', { class: 'botao botao-secundario',
            href: `#/desempenho?configuracoes=${enc(configuracoes.map((c) => c.id).join(','))}&ciclo=${enc(sessao.ciclo)}&sessao=${enc(id)}` },
          'Comparar as métricas no conjunto de teste'))));
  }

  desenhar();
  return { sair: () => visualizadores.forEach((v) => v.destruir()) };
}
