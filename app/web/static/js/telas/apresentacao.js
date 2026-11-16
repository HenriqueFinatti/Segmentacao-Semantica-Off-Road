// M02, conversa 2 (acesso ubíquo "Apresentar a recomendação"):
// O09.1 Retomar a análise · O09.2 Responder a uma dúvida (usa a O07.2) · O10 Registrar a decisão da coordenação.
import { api, enc } from '../api.js';
import { h, limpar, cabecalho, mensagem, falhaDaApi, anunciar, formato, erroCampo } from '../ui.js';
import { painelDiferenca, tabelaDesempenho } from './desempenho.js';
import { resumoConclusao } from './conclusao.js';

const DECISOES = [
  ['aceita', 'Aceita'],
  ['aceita com condição', 'Aceita com condição'],
  ['adiada', 'Adiada'],
];

export async function render(main, _p, consulta, contexto) {
  const ciclos = (await api.get('/api/ciclos')).filter((c) => c.recomendacao);

  limpar(main, cabecalho('Apresentar a recomendação', 'Retome a comparação e a recomendação do ciclo de testes e registre a decisão da coordenação.'));

  if (!ciclos.length) {
    main.append(mensagem('neutra', h('p', {}, 'Ainda não há recomendação registrada.'),
      h('p', {}, 'Registre uma recomendação em ', h('a', { href: '#/desempenho' }, 'Comparar o desempenho'), '.')));
    return null;
  }

  const ciclo = ciclos.some((c) => c.ciclo === consulta.get('ciclo')) ? consulta.get('ciclo') : ciclos[0].ciclo;
  let recomendacao = await api.get(`/api/recomendacoes?ciclo=${enc(ciclo)}`);
  let painel = null;
  const corpo = h('div', {});

  const seletor = h('select', { id: 'ciclo-apresentacao', onchange: (e) => contexto.navegar(`#/apresentar?ciclo=${enc(e.target.value)}`) },
    ciclos.map((c) => h('option', { value: c.ciclo, selected: c.ciclo === ciclo }, c.ciclo)));
  main.append(h('div', { class: 'campo', style: 'max-width:420px' }, h('label', { for: 'ciclo-apresentacao' }, 'Ciclo de testes'), seletor), corpo);

  function formularioDecisao() {
    const condicao = h('textarea', { id: 'condicao', name: 'condicao', disabled: true, 'aria-describedby': 'ajuda-condicao' });
    const botao = h('button', { type: 'submit', class: 'botao', disabled: true }, 'Registrar');
    const ajuda = h('span', { class: 'ajuda', id: 'ajuda-condicao' }, 'Escolha a decisão.');

    const form = h('form', { class: 'cartao', id: 'form-decisao', novalidate: true, tabindex: '-1' },
      h('h2', {}, 'Registrar a decisão da coordenação'),
      h('fieldset', { 'data-campo': 'decisao' }, h('legend', {}, 'Decisão'),
        DECISOES.map(([valor, rotulo]) => h('label', { class: 'opcao' }, h('input', { type: 'radio', name: 'decisao', value: valor }), rotulo))),
      h('div', { class: 'campo', 'data-campo': 'condicao' }, h('label', { for: 'condicao' }, 'Condição'), ajuda, condicao),
      h('div', { class: 'linha' }, botao,
        h('button', { type: 'button', class: 'botao botao-secundario', onclick: () => { painel = null; desenhar(); } }, 'Voltar à apresentação')));

    // Prevenção ativa: "aceita com condição" não pode ser registrada sem a condição
    const atualizar = () => {
      const decisao = form.querySelector('input[name="decisao"]:checked')?.value;
      const condicional = decisao === 'aceita com condição';
      condicao.disabled = !condicional;
      if (!condicional) condicao.value = '';
      const falta = condicional && !condicao.value.trim();
      botao.disabled = !decisao || falta;
      ajuda.textContent = !decisao ? 'Escolha a decisão.'
        : condicional ? (falta ? 'Informe a condição para poder registrar a decisão.' : 'O que precisa acontecer para a decisão valer.')
          : 'A condição só é usada quando a decisão é "aceita com condição".';
    };
    form.addEventListener('change', atualizar);
    condicao.addEventListener('input', atualizar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      try {
        recomendacao = await api.post(`/api/conclusoes/${enc(recomendacao.id)}/decisao`, {
          decisao: form.querySelector('input[name="decisao"]:checked')?.value, condicao: condicao.value,
        });
        painel = 'registrada';
        anunciar('Decisão registrada junto da recomendação.');
        desenhar();
      } catch (erro) {
        if (erro.tipo === 'PA') erroCampo(form, erro);
        else await falhaDaApi(erro, 'Não foi possível registrar a decisão');
      }
    });
    return form;
  }

  function textoDecisao(decisao) {
    if (decisao.decisao === 'aceita com condição') return `aceita, com a condição: ${decisao.condicao.replace(/[.!]+$/, '')}`;
    return decisao.decisao;
  }

  function desenhar() {
    const analise = recomendacao.analise;
    const decisao = recomendacao.decisao;
    const voltar = () => { painel = null; desenhar(); corpo.querySelector('[data-acao="diferenca"]')?.focus(); };

    limpar(corpo,
      // O09.1 Retomar a análise
      h('div', { class: 'cartao' },
        h('h2', {}, 'Recomendação do ciclo'),
        resumoConclusao(recomendacao, null)),
      analise ? h('div', { class: 'cartao' }, h('h2', {}, 'Comparação das configurações'), tabelaDesempenho(analise),
        h('p', { class: 'pequeno suave' }, `Comparação calculada em ${formato.data(analise.calculado_em)}.`),
        analise.configuracoes.length > 1 ? h('button', {
          type: 'button', class: 'botao botao-secundario', 'data-acao': 'diferenca',
          onclick: () => { painel = 'diferenca'; desenhar(); corpo.querySelector('#painel-diferenca')?.focus(); },
        }, 'A diferença importa?') : null) : null,
      painel === 'diferenca' && analise ? painelDiferenca(analise, { aoVoltar: voltar, rotuloVoltar: 'Voltar à apresentação' }) : null,
      decisao ? mensagem('ok', h('p', {}, h('strong', {}, 'Decisão registrada '), `junto da recomendação: ${textoDecisao(decisao)}.`),
        h('p', { class: 'pequeno' }, `Registrada em ${formato.data(decisao.registrada_em)}.`)) : null,
      painel === 'decisao' ? formularioDecisao() : null,
      !decisao && painel !== 'decisao' ? h('div', { class: 'linha' },
        h('button', { type: 'button', class: 'botao', onclick: () => { painel = 'decisao'; desenhar(); corpo.querySelector('#form-decisao')?.focus(); } },
          'Registrar a decisão')) : null);
  }

  desenhar();
  return null;
}
