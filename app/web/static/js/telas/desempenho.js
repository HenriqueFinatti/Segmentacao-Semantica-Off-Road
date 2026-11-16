// O06 Comparar o desempenho consolidado no conjunto de teste (M02 e M03):
// O06.1 Escolher as configurações · O06.2 Conferir se a comparação é válida · O06.3 Ler o desempenho ·
// O06.4 Consultar a matriz de confusão · O07.2 Julgar a diferença entre configurações (reusada na apresentação).
import { api, enc, ErroApi } from '../api.js';
import { h, limpar, cabecalho, mensagem, termo, dialogo, falhaDaApi, formato, situacao, conjuntoTexto } from '../ui.js';
import { graficoDeBarras, CORES_SERIES } from '../graficos.js';

export const LINHAS_METRICAS = [
  { chave: 'miou', rotulo: 'IoU médio', termo: 'iou_medio' },
  { chave: 'iou_trilha', rotulo: 'IoU da classe Trilha', termo: 'iou_trilha' },
  { chave: 'iou_fundo', rotulo: 'IoU da classe Fora da trilha', termo: 'iou_fundo' },
  { chave: 'acuracia', rotulo: 'Acurácia', termo: 'acuracia' },
  { chave: 'tempo_inferencia_ms', rotulo: 'Tempo de inferência', termo: 'tempo_inferencia', tempo: true },
];

const valorTexto = (linha, valor) => (linha.tempo ? formato.ms(valor) : formato.metrica(valor));

export function tabelaMatriz(matriz, nome) {
  const trilha = matriz.tp + matriz.fn;
  const fora = matriz.tn + matriz.fp;
  const fracao = (valor, total) => (total ? valor / total : null);
  return h('div', {},
    h('table', { class: 'matriz' },
      h('caption', { class: 'oculto-visual' }, `Matriz de confusão da ${nome} no conjunto de teste`),
      h('thead', {}, h('tr', {}, h('th', {}, 'Classe anotada'), h('th', {}, 'Marcada como Trilha'), h('th', {}, 'Marcada como Fora da trilha'))),
      h('tbody', {},
        h('tr', {}, h('th', {}, 'Trilha'),
          h('td', {}, h('strong', {}, formato.porcento(fracao(matriz.tp, trilha))), h('br'), h('span', { class: 'pequeno suave' }, `${formato.inteiro(matriz.tp)} pontos (acerto)`)),
          h('td', {}, h('strong', {}, formato.porcento(fracao(matriz.fn, trilha))), h('br'), h('span', { class: 'pequeno suave' }, `${formato.inteiro(matriz.fn)} pontos (erro)`))),
        h('tr', {}, h('th', {}, 'Fora da trilha'),
          h('td', {}, h('strong', {}, formato.porcento(fracao(matriz.fp, fora))), h('br'), h('span', { class: 'pequeno suave' }, `${formato.inteiro(matriz.fp)} pontos (erro)`)),
          h('td', {}, h('strong', {}, formato.porcento(fracao(matriz.tn, fora))), h('br'), h('span', { class: 'pequeno suave' }, `${formato.inteiro(matriz.tn)} pontos (acerto)`))))),
    h('p', { class: 'pequeno' }, `Do que era Trilha, ${formato.porcento(fracao(matriz.fn, trilha))} foi marcado como Fora da trilha; `
      + `do que era Fora da trilha, ${formato.porcento(fracao(matriz.fp, fora))} foi marcado como Trilha.`));
}

// O06.3: tabela com o valor de referência (origem indicada) e o destaque do maior valor
export function tabelaDesempenho(analise) {
  const configuracoes = analise.configuracoes;
  const referencia = analise.referencia;

  const cabecalhoTabela = h('tr', {}, h('th', {}, 'Métrica'),
    configuracoes.map((c) => h('th', { class: 'numero', scope: 'col' }, c.nome)),
    h('th', { class: 'numero', scope: 'col' }, termo('Valor de referência', 'valor_de_referencia')));

  const linhas = LINHAS_METRICAS.map((linha) => h('tr', {},
    h('th', { scope: 'row' }, termo(linha.rotulo, linha.termo)),
    configuracoes.map((c) => {
      const maior = (analise.maior_valor?.[linha.chave] || []).includes(c.id);
      return h('td', { class: `numero ${maior ? 'maior-valor' : ''}` }, valorTexto(linha, c.metricas[linha.chave]),
        maior ? h('span', { class: 'marca-maior' }, '▲ maior valor') : null);
    }),
    h('td', { class: 'numero' }, referencia ? valorTexto(linha, referencia.metricas[linha.chave]) : '—')));

  return h('div', {},
    h('div', { class: 'tabela-rolagem' }, h('table', {},
      h('caption', { class: 'oculto-visual' }, 'Desempenho de cada configuração no conjunto de teste'),
      h('thead', {}, cabecalhoTabela), h('tbody', {}, linhas))),
    h('p', { class: 'pequeno', style: 'margin-top:.5rem' },
      h('strong', {}, 'Origem da referência: '),
      referencia ? referencia.origem : 'ainda não há configuração em uso (nenhuma foi executada), por isso não há valor de referência', '.'),
    h('p', { class: 'pequeno suave' }, termo('Maior valor', 'maior_valor'),
      ': destaca a configuração com o maior valor em cada métrica para organizar a leitura; não é uma recomendação. '
      + 'O tempo de inferência não é destacado porque depende do computador.'));
}

// O07.2 Julgar a diferença entre configurações: mostra a diferença e o limite da métrica, sem julgar
export function painelDiferenca(analise, { aoVoltar, rotuloVoltar = 'Voltar à análise' } = {}) {
  const configuracoes = analise.configuracoes;
  const estado = { a: configuracoes[0]?.id, b: configuracoes[1]?.id, metrica: 'miou' };
  const conteudo = h('div', { 'aria-live': 'polite' });

  const seletor = (chave, rotulo) => h('label', { class: 'linha' }, h('span', { class: 'rotulo' }, rotulo),
    h('select', { onchange: (e) => { estado[chave] = e.target.value; desenhar(); } },
      (chave === 'metrica' ? LINHAS_METRICAS.map((l) => [l.chave, l.rotulo]) : configuracoes.map((c) => [c.id, c.nome]))
        .map(([valor, texto]) => h('option', { value: valor, selected: estado[chave] === valor }, texto))));

  function desenhar() {
    const a = configuracoes.find((c) => c.id === estado.a);
    const b = configuracoes.find((c) => c.id === estado.b);
    const linha = LINHAS_METRICAS.find((l) => l.chave === estado.metrica);
    if (!a || !b || a.id === b.id) {
      limpar(conteudo, h('p', {}, 'Escolha duas configurações diferentes.'));
      return;
    }
    const va = a.metricas[linha.chave];
    const vb = b.metricas[linha.chave];
    const diferenca = va !== null && vb !== null ? va - vb : null;
    const textoDiferenca = linha.tempo ? `${diferenca > 0 ? '+' : ''}${formato.ms(diferenca)}` : formato.diferenca(diferenca);

    const limites = {
      miou: 'O IoU médio resume o acerto geral; ele não mostra em que tipo de trecho cada configuração erra.',
      iou_trilha: 'O IoU da classe Trilha mostra quanto a trilha marcada coincide com a anotada; ele não mostra em que tipo de trecho cada configuração erra.',
      iou_fundo: 'O IoU da classe Fora da trilha costuma ser alto porque a maior parte da imagem fica fora da trilha; sozinho, ele não mostra se a trilha foi bem reconhecida.',
      acuracia: 'A acurácia pode ser alta mesmo quando a trilha é pouco reconhecida, porque a maior parte da imagem é Fora da trilha.',
      tempo_inferencia_ms: 'O tempo de inferência depende do computador usado; em outra máquina a diferença pode ser outra.',
    };

    limpar(conteudo,
      mensagem('neutra',
        h('p', {}, `A `, h('strong', {}, 'diferença entre configurações'), ` (${a.nome} − ${b.nome}) é de `, h('strong', {}, textoDiferenca),
          ` no ${linha.rotulo}, no conjunto de teste.`),
        h('p', {}, 'Não indico se ela é relevante: isso depende do critério de vocês.'),
        h('p', {}, limites[linha.chave], ' Nenhuma métrica garante que um trajeto é seguro.'),
        analise.conjuntos_iguais === false ? h('p', {}, h('strong', {}, 'Atenção: '), 'estas configurações foram avaliadas em conjuntos de teste diferentes.') : null));
  }

  desenhar();
  return h('div', { class: 'cartao', id: 'painel-diferenca', tabindex: '-1' },
    h('h2', {}, 'A diferença importa?'),
    h('div', { class: 'linha', style: 'margin-bottom:.6rem' },
      seletor('a', 'Configuração'), seletor('b', 'comparada com'), seletor('metrica', 'Métrica')),
    conteudo,
    aoVoltar ? h('button', { type: 'button', class: 'botao botao-secundario', onclick: aoVoltar }, rotuloVoltar) : null);
}

export async function render(main, _p, consulta) {
  const [configuracoes, ciclos] = await Promise.all([api.get('/api/configuracoes'), api.get('/api/ciclos')]);
  const disponiveis = configuracoes.filter((c) => c.disponivel);
  const pedidas = (consulta.get('configuracoes') || '').split(',').filter(Boolean);
  const sessaoOrigem = consulta.get('sessao');
  const estado = {
    ciclo: consulta.has('ciclo') ? consulta.get('ciclo') : (ciclos[0]?.ciclo || ''),
    selecionadas: pedidas,
    analise: null,
    painel: null,
    grafico: false,
    compararMesmoAssim: false,
  };

  const escolha = h('div', {});
  const resultado = h('div', { id: 'resultado-desempenho' });
  limpar(main, cabecalho('Comparar o desempenho',
    'Compare as métricas das configurações no conjunto de teste e registre a recomendação ou a conclusão do experimento.',
    sessaoOrigem ? h('a', { href: `#/sessao/${enc(sessaoOrigem)}/comparar` }, '← Comparar na mesma imagem e região') : null),
  escolha, resultado);

  if (!disponiveis.length) {
    limpar(escolha, mensagem('neutra', h('p', {}, 'Ainda não há configuração treinada para comparar.')));
    return null;
  }

  const ciclo = (nome) => ciclos.find((c) => c.ciclo === nome);

  // O06.1 Escolher as configurações
  function desenharEscolha() {
    const executadasNoCiclo = new Set(ciclo(estado.ciclo)?.configuracoes || []);
    const seletorCiclo = h('select', { id: 'ciclo-desempenho', onchange: (e) => { estado.ciclo = e.target.value; desenharEscolha(); } },
      h('option', { value: '', selected: !estado.ciclo }, 'Todas as configurações (sem filtrar por ciclo)'),
      ciclos.map((c) => h('option', { value: c.ciclo, selected: c.ciclo === estado.ciclo }, c.ciclo)));

    const lista = h('div', { class: 'lista-configuracoes', role: 'group', 'aria-label': 'Configurações' },
      disponiveis.map((c) => {
        const idCampo = `desempenho-${c.id}`;
        const semExecucao = estado.ciclo && !executadasNoCiclo.has(c.id);
        return h('label', { class: 'item-configuracao', for: idCampo },
          h('input', { type: 'checkbox', id: idCampo, value: c.id, checked: estado.selecionadas.includes(c.id),
            onchange: (e) => {
              estado.selecionadas = e.target.checked ? [...estado.selecionadas, c.id] : estado.selecionadas.filter((x) => x !== c.id);
            } }),
          h('span', {},
            h('span', { class: 'nome' }, c.nome), situacao(c.situacao),
            h('span', { class: 'descricao', style: 'display:block' }, c.descricao),
            h('span', { class: 'pequeno', style: 'display:block' },
              c.teste ? conjuntoTexto(c.teste.conjunto) : 'Sem avaliação no conjunto de teste'),
            estado.ciclo ? h('span', { class: 'pequeno', style: `display:block;${semExecucao ? 'color:var(--alerta);font-weight:600' : ''}` },
              semExecucao ? 'Sem execução concluída neste ciclo de testes' : 'Com execução concluída neste ciclo de testes') : null));
      }));

    limpar(escolha, h('form', { class: 'cartao', novalidate: true, onsubmit: (e) => { e.preventDefault(); estado.compararMesmoAssim = false; comparar(); } },
      h('h2', {}, 'Escolher as configurações'),
      h('div', { class: 'campo' }, h('label', { for: 'ciclo-desempenho' }, termo('Ciclo de testes', 'ciclo_de_testes')), seletorCiclo),
      lista,
      h('p', { class: 'erro-campo', role: 'alert', id: 'erro-escolha' }),
      h('div', { class: 'linha', style: 'margin-top:.75rem' }, h('button', { type: 'submit', class: 'botao' }, 'Comparar as selecionadas'))));
  }

  async function comparar() {
    const aviso = escolha.querySelector('#erro-escolha');
    if (!estado.selecionadas.length) { aviso.textContent = 'Escolha pelo menos uma configuração para comparar.'; return; }
    aviso.textContent = '';

    try {
      estado.analise = await api.post('/api/desempenho', {
        configuracoes: estado.selecionadas, ciclo: estado.ciclo || null, comparar_mesmo_assim: estado.compararMesmoAssim,
      });
      estado.painel = null;
      desenharResultado();
      resultado.querySelector('h2')?.focus();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      const ruptura = erro.dados?.ruptura;

      if (ruptura === 'execucao_faltante') {
        // Captura de erro: o que falta e o que fazer fora do sistema
        await dialogo({
          tipo: 'falha', titulo: 'Configuração sem execução neste ciclo',
          corpo: h('div', {},
            erro.dados.configuracoes.map((nome) => h('p', {}, `A configuração ${nome} ainda não tem execução concluída no ciclo de testes "${erro.dados.ciclo}".`)),
            h('p', {}, 'Para incluí-la, peça a execução ao integrante que executa os modelos.')),
          acoes: [{ rotulo: 'Entendi', valor: 'ok', primaria: true }],
        });
      } else if (ruptura === 'sem_avaliacao_no_teste') {
        await dialogo({
          tipo: 'falha', titulo: 'Configuração sem avaliação no conjunto de teste',
          corpo: h('div', {},
            erro.dados.configuracoes.map((nome) => h('p', {}, `A configuração ${nome} ainda não foi avaliada no conjunto de teste.`)),
            h('p', {}, 'Peça a avaliação a quem prepara os datasets (tela Datasets).')),
          acoes: [{ rotulo: 'Entendi', valor: 'ok', primaria: true }],
        });
      } else if (ruptura === 'conjuntos_diferentes') {
        // O06.2 Conferir se a comparação é válida (alerta)
        const escolhaAlerta = await dialogo({
          tipo: 'alerta', titulo: 'Conjuntos de teste diferentes',
          corpo: h('div', {},
            h('p', {}, 'As configurações escolhidas foram avaliadas em conjuntos de teste diferentes. Comparar resultados de conjuntos diferentes pode levar a uma conclusão errada.'),
            h('ul', {}, erro.dados.conjuntos.map((item) => h('li', {}, `${item.configuracao}: ${conjuntoTexto(item.conjunto)}`)))),
          acoes: [{ rotulo: 'Escolher outras configurações', valor: 'outras', primaria: true }, { rotulo: 'Comparar mesmo assim', valor: 'mesmo assim' }],
        });
        if (escolhaAlerta === 'mesmo assim') {
          estado.compararMesmoAssim = true;
          await comparar();
        } else {
          escolha.querySelector('input[type="checkbox"]')?.focus();
        }
      } else {
        await falhaDaApi(erro, 'Não foi possível comparar');
      }
    }
  }

  // O06.3 Ler o desempenho de cada configuração (com O06.4 e O07.2 abertos a partir dela)
  function desenharResultado() {
    const analise = estado.analise;
    if (!analise) { limpar(resultado); return; }
    const varias = analise.configuracoes.length > 1;
    const voltar = () => { estado.painel = null; desenharResultado(); resultado.querySelector(`[data-acao]`)?.focus(); };
    const conjunto = analise.configuracoes[0].conjunto;

    const grafico = estado.grafico ? graficoDeBarras({
      titulo: 'Métricas no conjunto de teste (de 0 a 1)',
      nomes: analise.configuracoes.map((c) => c.nome),
      cores: CORES_SERIES,
      grupos: LINHAS_METRICAS.filter((l) => !l.tempo).map((l) => ({
        rotulo: l.rotulo, valores: analise.configuracoes.map((c) => ({ nome: c.nome, valor: c.metricas[l.chave] })),
      })),
    }) : null;

    const parametrosConclusao = `configuracoes=${enc(analise.configuracoes.map((c) => c.id).join(','))}`
      + `&ciclo=${enc(analise.ciclo || '')}&comparar_mesmo_assim=${estado.compararMesmoAssim ? '1' : ''}`
      + (sessaoOrigem ? `&sessao=${enc(sessaoOrigem)}` : '');

    limpar(resultado,
      h('div', { class: 'cartao' },
        h('h2', { tabindex: '-1' }, 'Desempenho de cada configuração'),
        analise.conjuntos_iguais
          ? mensagem('ok', h('p', {}, varias ? `As ${analise.configuracoes.length} configurações foram avaliadas no mesmo ` : 'Avaliada no ',
            termo('conjunto de teste', 'conjunto_de_teste'), varias ? '. A comparação é válida.' : '.'), h('p', { class: 'pequeno' }, conjuntoTexto(conjunto)))
          : mensagem('alerta', h('p', {}, 'Estas configurações foram avaliadas em conjuntos de teste diferentes; a comparação pode levar a uma conclusão errada.')),
        tabelaDesempenho(analise),
        h('p', { class: 'pequeno suave' }, 'Imagens sem anotação de referência, como as dos testes de campo, não têm métricas e são avaliadas visualmente.'),
        h('div', { class: 'linha' },
          h('button', { type: 'button', class: 'botao botao-secundario', 'aria-pressed': String(estado.grafico),
            onclick: () => { estado.grafico = !estado.grafico; desenharResultado(); } }, estado.grafico ? 'Esconder o gráfico' : 'Ver também em gráfico'),
          varias ? h('button', { type: 'button', class: 'botao botao-secundario', 'data-acao': 'diferenca',
            onclick: () => { estado.painel = 'diferenca'; desenharResultado(); resultado.querySelector('#painel-diferenca')?.focus(); } }, 'A diferença importa?') : null,
          h('button', { type: 'button', class: 'botao botao-secundario', 'data-acao': 'matriz',
            onclick: () => { estado.painel = 'matriz'; desenharResultado(); resultado.querySelector('#painel-matriz')?.focus(); } }, 'Onde cada uma erra?')),
        grafico ? h('div', { style: 'margin-top:1rem' }, grafico) : null),
      estado.painel === 'diferenca' ? painelDiferenca(analise, { aoVoltar: voltar }) : null,
      estado.painel === 'matriz' ? h('div', { class: 'cartao', id: 'painel-matriz', tabindex: '-1' },
        h('h2', {}, termo('Matriz de confusão', 'matriz_confusao'), ' no conjunto de teste'),
        h('div', { class: 'grade-2' }, analise.configuracoes.map((c) => h('div', {}, h('h3', {}, c.nome), tabelaMatriz(c.matriz, c.nome)))),
        h('button', { type: 'button', class: 'botao botao-secundario', onclick: voltar }, 'Voltar à análise')) : null,
      h('div', { class: 'cartao' },
        h('h2', {}, 'Registrar a conclusão'),
        h('p', { class: 'pequeno suave' }, 'A conclusão é sua: o sistema registra o que você decidir junto desta comparação.'),
        h('div', { class: 'linha' },
          h('a', { class: 'botao', href: `#/conclusao/nova?tipo=${enc('recomendação')}&${parametrosConclusao}` }, 'Registrar a recomendação'),
          h('a', { class: 'botao botao-secundario', href: `#/conclusao/nova?tipo=experimento&${parametrosConclusao}` }, 'Registrar a conclusão do experimento'))));
  }

  desenharEscolha();
  if (pedidas.length) await comparar();
  return null;
}
