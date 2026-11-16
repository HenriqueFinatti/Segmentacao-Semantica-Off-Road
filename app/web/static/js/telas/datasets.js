// Tela de apoio (fora dos MoLIC): baixar os datasets brutos para raw/, montar o dataset e avaliar
// as configurações no conjunto de teste atual. raw/ nunca é apagado: remontar não exige baixar de novo.
import { api, enc } from '../api.js';
import { h, limpar, cabecalho, mensagem, estado, progresso, dialogo, falhaDaApi, anunciar, formato, conjuntoTexto } from '../ui.js';

export async function render(main, _p, _c, contexto) {
  let dados = await api.get('/api/datasets');
  const corpo = h('div', {});
  limpar(main, cabecalho('Datasets', 'Prepare os dados do TCC: baixe os datasets brutos, monte o dataset e avalie as configurações no conjunto de teste.'),
    mensagem('neutra', h('p', { class: 'pequeno' }, 'Esta tela prepara os dados para o treino e para as métricas. As imagens dos testes de campo são enviadas em ',
      h('a', { href: '#/segmentar' }, 'Segmentar imagens'), '.')),
    corpo);

  async function executar(promessa, mensagemOk) {
    try {
      await promessa;
      anunciar(mensagemOk);
      await contexto.atualizarEstado();
      dados = await api.get('/api/datasets');
      desenhar();
    } catch (erro) {
      await falhaDaApi(erro);
    }
  }

  function tarefasAtivas() {
    return (contexto.estado?.tarefas || []).filter((t) => t.tipo === 'dataset');
  }

  function desenhar() {
    const ativas = tarefasAtivas();
    const ocupado = ativas.length > 0;

    const linhas = dados.datasets.map((d) => {
      const tarefa = ativas.find((t) => t.alvo?.dataset === d.id);
      let acao;
      if (tarefa) acao = h('div', {}, estado(tarefa.estado), progresso(tarefa.progresso.atual, tarefa.progresso.total, tarefa.progresso.texto));
      else if (d.bruto_disponivel) acao = h('span', { class: 'pequeno' }, 'Arquivos brutos guardados.');
      else if (d.pode_baixar) {
        acao = h('button', { type: 'button', class: 'botao botao-pequeno', disabled: ocupado,
          onclick: () => executar(api.post(`/api/datasets/${enc(d.id)}/baixar`), `Download do ${d.nome} na fila.`) }, `Baixar ${d.nome}`);
      } else {
        acao = h('span', { class: 'pequeno' }, 'Copie a pasta CaSSed_Dataset (extraída do CaSSeD.tar.gz) para raw/CaSSed_Dataset.');
      }
      return h('tr', {},
        h('th', { scope: 'row' }, d.nome),
        h('td', {}, d.bruto_disponivel ? h('span', { class: 'marcador marcador-correta' }, '✓ disponível') : h('span', { class: 'marcador marcador-sem' }, 'ausente')),
        h('td', { class: 'numero' }, formato.inteiro(d.imagens_treino)),
        h('td', { class: 'numero' }, formato.inteiro(d.imagens_teste)),
        h('td', {}, acao));
    });

    const montagem = ativas.find((t) => t.alvo?.dataset === 'todos');
    const brutos = dados.datasets.filter((d) => d.bruto_disponivel);
    const avaliacoes = ativas.filter((t) => t.alvo?.configuracao);

    // Falhas recentes: causa e o que fazer, em linguagem de usuário
    const falhas = (contexto.estado?.tarefas_recentes || []).filter((t) => t.tipo === 'dataset' && t.estado === 'falhou').slice(-3);

    limpar(corpo,
      falhas.map((t) => mensagem('falha', h('p', {}, h('strong', {}, 'Falhou: '), `${t.titulo} não terminou porque ${t.causa}.`),
        t.sugestao ? h('p', {}, t.sugestao) : null)),
      h('div', { class: 'cartao' },
        h('h2', {}, 'Datasets do TCC'),
        h('div', { class: 'tabela-rolagem' }, h('table', {},
          h('thead', {}, h('tr', {}, h('th', {}, 'Dataset'), h('th', {}, 'Arquivos brutos (raw/)'), h('th', { class: 'numero' }, 'Imagens de treino'),
            h('th', { class: 'numero' }, 'Imagens de teste'), h('th', {}, 'Ação'))),
          h('tbody', {}, linhas)))),
      h('div', { class: 'cartao' },
        h('h2', {}, 'Montar o dataset'),
        dados.montagem ? h('p', {}, `Montado em ${formato.data(dados.montagem.data)}${dados.montagem.datasets?.length ? ` com ${dados.montagem.datasets.join(', ')}` : ''}.`)
          : h('p', {}, 'O dataset ainda não foi montado pela interface.'),
        h('p', {}, h('strong', {}, 'Conjunto de teste atual: '), dados.conjunto_de_teste ? conjuntoTexto(dados.conjunto_de_teste) : 'nenhum.'),
        montagem ? h('div', {}, estado(montagem.estado), progresso(montagem.progresso.atual, montagem.progresso.total, montagem.progresso.texto))
          : h('button', { type: 'button', class: 'botao', disabled: ocupado || !brutos.length, onclick: confirmarMontagem }, 'Remontar o dataset'),
        !brutos.length ? h('p', { class: 'pequeno suave' }, 'Baixe ou copie pelo menos um dataset bruto para montar.') : null),
      h('div', { class: 'cartao' },
        h('h2', {}, 'Avaliar no conjunto de teste'),
        avaliacoes.length ? avaliacoes.map((t) => h('div', { style: 'margin-bottom:.5rem' }, h('div', { class: 'linha' }, h('strong', {}, t.titulo), estado(t.estado)),
          progresso(t.progresso.atual, t.progresso.total, t.progresso.texto))) : null,
        dados.configuracoes_a_avaliar.length ? formularioAvaliacao(ocupado)
          : h('p', {}, 'Todas as configurações disponíveis estão avaliadas no conjunto de teste atual.')));
  }

  function formularioAvaliacao(ocupado) {
    const form = h('form', { novalidate: true },
      h('p', { class: 'pequeno' }, 'Estas configurações precisam ser avaliadas no conjunto de teste atual para entrar na comparação de desempenho:'),
      dados.configuracoes_a_avaliar.map((c) => h('label', { class: 'opcao' },
        h('input', { type: 'checkbox', name: 'configuracoes', value: c.id, checked: true }), h('span', {}, c.nome, h('span', { class: 'pequeno suave' }, ` · ${c.motivo}`)))),
      h('button', { type: 'submit', class: 'botao', disabled: ocupado }, 'Avaliar as selecionadas'));
    form.addEventListener('submit', (evento) => {
      evento.preventDefault();
      const configuracoes = new FormData(form).getAll('configuracoes');
      if (configuracoes.length) executar(api.post('/api/datasets/avaliar', { configuracoes }), 'Avaliação na fila.');
    });
    return form;
  }

  async function confirmarMontagem() {
    const escolha = await dialogo({
      tipo: 'alerta', titulo: 'Remontar o dataset',
      corpo: h('div', {},
        h('p', {}, 'O dataset montado será substituído por uma nova cópia feita a partir dos arquivos brutos de raw/. Os arquivos brutos não mudam.'),
        h('p', {}, 'O conjunto de teste pode mudar. As configurações avaliadas no conjunto anterior precisarão ser avaliadas de novo para entrar na mesma comparação.')),
      acoes: [{ rotulo: 'Cancelar', valor: 'cancelar' }, { rotulo: 'Remontar', valor: 'remontar', primaria: true }],
    });
    if (escolha === 'remontar') executar(api.post('/api/datasets/remontar'), 'Montagem do dataset na fila.');
  }

  desenhar();

  let ultimo = '';
  return {
    async atualizar() {
      const ativas = tarefasAtivas().map((t) => [t.id, t.estado, t.progresso.atual, t.progresso.texto]);
      const chave = JSON.stringify(ativas);
      if (chave === ultimo) return;
      const terminou = ultimo && ativas.length < JSON.parse(ultimo).length;
      ultimo = chave;
      if (terminou || !ativas.length) dados = await api.get('/api/datasets');
      desenhar();
    },
  };
}
