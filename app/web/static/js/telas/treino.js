// M03, conversa 1 (treinar e avaliar uma nova configuração):
// O01.1 Escolher o modelo e os parâmetros e O01.2 Nomear a configuração (na mesma tela) ·
// O02.1 Acompanhar o treino (estado do treino e da avaliação no conjunto de teste; ruptura "treino ou avaliação interrompidos") ·
// O02.2 Conferir o resultado do treino (só depois da avaliação no conjunto de teste).
import { api, enc, ErroApi } from '../api.js';
import {
  h, limpar, cabecalho, mensagem, estado, progresso, erroCampo, falhaDaApi, anunciar, formato,
  conjuntoTexto, exigir,
} from '../ui.js';
import { graficoDeLinhas } from '../graficos.js';
import { tabelaMatriz } from './desempenho.js';
const tarefaAvaliacao = (estadoGeral, cid) => (estadoGeral?.tarefas || []).find((t) => t.tipo === 'avaliacao' && t.alvo?.configuracao === cid);


export async function renderNovo(main, _p, _consulta, contexto) {
  const padroes = await api.get('/api/treino/padroes');
  const montados = new Set(padroes.datasets.filter((d) => d.imagens_treino > 0).map((d) => d.id));
  // Só os datasets montados podem ser escolhidos (prevenção ativa)
  // Estado inicial da tela: early stopping ligado, execução de teste desligada
  const valores = { ...padroes.padrao, modelo: 'deeplabv3+', nome: '', early_stopping: true, execucao_teste: false };
  valores.datasets = valores.datasets.filter((d) => montados.has(d));
  // O campo Épocas é um só: mostra as épocas do treino normal ou as da execução de teste, e guarda cada valor
  const epocasPorModo = { normal: String(padroes.padrao.epocas), teste: String(padroes.padrao.execucao_teste_epocas) };

  const corpo = h('div', {});
  limpar(main, cabecalho('Treinar uma configuração',
    'Defina o nome, o modelo e os parâmetros de treino. Os valores já preenchidos são os padrões do TCC.'), corpo);

  function numero(campo, rotulo, ajuda, extra = {}) {
    return h('div', { class: 'campo', 'data-campo': campo },
      h('label', { for: campo }, rotulo),
      ajuda ? h('span', { class: 'ajuda', id: `ajuda-${campo}` }, ajuda) : null,
      h('input', {
        type: 'number', id: campo, name: campo, min: '1', step: '1', value: String(valores[campo] ?? ''), inputmode: 'numeric',
        'aria-describedby': ajuda ? `ajuda-${campo}` : null, ...extra,
      }));
  }

  const inteiroPositivo = (formulario, id) => {
    const campo = formulario.querySelector(`#${id}`);
    return campo.disabled || (/^\d+$/.test(campo.value.trim()) && Number(campo.value) >= 1);
  };

  function desenharFormulario() {
    const botao = h('button', { type: 'submit', class: 'botao' }, 'Iniciar o treino');
    const campoNome = h('input', { type: 'text', id: 'nome', name: 'nome', autocomplete: 'off', 'aria-describedby': 'ajuda-nome' });
    // Esquerda: nome, modelo, as escolhas de early stopping e execução de teste e o batch size.
    // Direita: datasets e, abaixo deles, os campos que aparecem conforme essas escolhas.
    const formulario = h('form', { class: 'cartao', novalidate: true },
      h('div', { class: 'grade-2' },
        h('div', {},
          h('div', { class: 'campo', 'data-campo': 'nome' },
            h('label', { for: 'nome' }, 'Nome da configuração'),
            h('span', { class: 'ajuda', id: 'ajuda-nome' },
              'Sugerido a partir do modelo, da data e da hora, sem repetir um nome existente. Você pode trocar. O nome identifica a configuração para toda a equipe.'),
            campoNome),
          h('fieldset', { 'data-campo': 'modelo' }, h('legend', {}, 'Modelo'),
            padroes.modelos.map((m) => h('label', { class: 'opcao' },
              h('input', { type: 'radio', name: 'modelo', value: m.id, checked: valores.modelo === m.id }), m.nome))),
          h('div', { class: 'linha' },
            h('label', { class: 'opcao' }, h('input', { type: 'checkbox', name: 'early_stopping', id: 'early_stopping', checked: valores.early_stopping }),
              'Early stopping')),
          h('div', { class: 'linha' },
            h('label', { class: 'opcao' }, h('input', { type: 'checkbox', name: 'execucao_teste', id: 'execucao_teste', checked: valores.execucao_teste }),
              'Execução de teste')),
          numero('batch_size', 'Batch size', 'Valores maiores exigem mais memória do computador.')),
        h('div', { class: 'coluna-dinamica' },
          h('fieldset', { 'data-campo': 'datasets' },
            h('legend', {}, 'Datasets de treino'),
            h('p', { class: 'pequeno suave', style: 'margin:0 0 .3rem' }, 'Só os datasets montados podem ser escolhidos.'),
            padroes.datasets.map((d) => {
              const vazio = !montados.has(d.id);
              return h('label', { class: `opcao ${vazio ? 'desabilitada' : ''}` },
                h('input', { type: 'checkbox', name: 'datasets', value: d.id, checked: valores.datasets.includes(d.id), disabled: vazio }),
                h('span', {}, d.nome, h('span', { class: 'pequeno suave', style: 'display:block' },
                  vazio ? 'Não está no dataset montado (monte-o na tela Datasets).' : `${formato.inteiro(d.imagens_treino)} imagens de treino no dataset montado`)));
            })),
          numero('paciencia', 'Paciência', 'Épocas sem melhora na validação até encerrar. Com o early stopping ligado, o treino continua até ele parar.'),
          // Épocas logo abaixo dos datasets: mesma posição no treino normal e na execução de teste
          numero('epocas', 'Épocas', 'Número de épocas do treino.', { value: epocasPorModo.normal }),
          numero('execucao_teste_imagens', 'Imagens da execução de teste', 'Quantas imagens o treino usa (mínimo 3: 2 de treino e 1 de validação).',
            { min: '3' }))),
      h('p', { class: 'pequeno suave' }, 'Os parâmetros internos do treino (taxa de aprendizado, tamanho da imagem e outros) são fixos do TCC. Os gráficos de treino são sempre gerados.'),
      h('div', { class: 'linha' }, botao));

    const caixaEarly = formulario.querySelector('#early_stopping');
    const caixaTeste = formulario.querySelector('#execucao_teste');

    // Nome sugerido ("modelo - data hora"): acompanha o modelo até a pessoa editar o nome
    let nomeEditado = false;
    let pedidoSugestao = 0;
    async function sugerirNome() {
      if (nomeEditado) return;
      lerFormulario(formulario);
      const pedido = ++pedidoSugestao;
      try {
        const sugestao = await api.get(`/api/treino/nome-sugerido?modelo=${enc(valores.modelo)}`);
        if (pedido !== pedidoSugestao || nomeEditado) return;
        campoNome.value = sugestao.nome;
        regras.atualizar();
      } catch {
        // Sem sugestão a pessoa digita o nome
      }
    }
    campoNome.addEventListener('input', () => {
      nomeEditado = campoNome.value.trim().length > 0;
      erroCampo(formulario, null);
    });
    formulario.addEventListener('change', (evento) => {
      if (evento.target.name === 'modelo') sugerirNome();
    });
    // O que aparece na tela:
    // - early stopping ligado: Paciência; sem Épocas (o treino continua até o early stopping parar)
    // - early stopping desligado: Épocas no lugar da Paciência
    // - Batch size fica sempre visível, na coluna da esquerda
    // - execução de teste ligada: desliga o early stopping e mostra as imagens de teste e as Épocas (com o valor do teste)
    const campoEpocas = formulario.querySelector('#epocas');
    const mostrar = (campo, visivel) => {
      formulario.querySelector(`[data-campo="${campo}"]`).hidden = !visivel;
      formulario.querySelector(`#${campo}`).disabled = !visivel;
    };
    const mostrarCampos = () => {
      const teste = caixaTeste.checked;
      const early = caixaEarly.checked && !teste;
      mostrar('paciencia', early);
      mostrar('execucao_teste_imagens', teste);
      mostrar('epocas', !early);
      formulario.querySelector('[data-campo="epocas"] .ajuda').textContent = teste
        ? 'Épocas da execução de teste.' : 'Número de épocas do treino.';
    };
    // Early stopping e execução de teste se excluem, e um clique em qualquer um deles basta:
    // marcar um desmarca o outro; desmarcar um só desmarca ele mesmo.
    const trocarModoDasEpocas = (teste) => {
      // O campo Épocas guarda um valor para o treino normal e outro para a execução de teste
      epocasPorModo[teste ? 'normal' : 'teste'] = campoEpocas.value;
      campoEpocas.value = epocasPorModo[teste ? 'teste' : 'normal'];
    };
    caixaEarly.addEventListener('change', () => {
      if (caixaEarly.checked && caixaTeste.checked) {
        caixaTeste.checked = false;
        trocarModoDasEpocas(false);
      }
      mostrarCampos();
    });
    caixaTeste.addEventListener('change', () => {
      trocarModoDasEpocas(caixaTeste.checked);
      if (caixaTeste.checked) caixaEarly.checked = false;
      mostrarCampos();
    });
    mostrarCampos();

    const regras = exigir(formulario, botao, [
      { campo: 'nome', valido: () => campoNome.value.trim().length > 0 },
      { campo: 'epocas', valido: () => inteiroPositivo(formulario, 'epocas') },
      { campo: 'paciencia', valido: () => inteiroPositivo(formulario, 'paciencia') },
      { campo: 'batch_size', valido: () => inteiroPositivo(formulario, 'batch_size') },
      {
        campo: 'execucao_teste_imagens',
        valido: () => inteiroPositivo(formulario, 'execucao_teste_imagens')
          && (formulario.querySelector('#execucao_teste_imagens').disabled || Number(formulario.querySelector('#execucao_teste_imagens').value) >= 3),
      },
      {
        campo: 'datasets', valido: () => formulario.querySelectorAll('input[name="datasets"]:checked').length > 0,
      },
    ]);
    caixaEarly.addEventListener('change', regras.atualizar);
    caixaTeste.addEventListener('change', regras.atualizar);

    formulario.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      if (!regras.atualizar()) return;
      lerFormulario(formulario);
      valores.nome = campoNome.value.trim();
      botao.disabled = true;
      try {
        const configuracao = await api.post('/api/treino', valores);
        anunciar(configuracao.treino?.estado === 'na fila' ? `Treino na fila: ${configuracao.nome}.` : `Treino iniciado com a ${configuracao.nome}.`);
        await contexto.atualizarEstado();
        contexto.navegar(`#/treino/${enc(configuracao.id)}`);
      } catch (erro) {
        regras.atualizar();
        // Parâmetro recusado ou nome que repete um existente: o aviso aparece junto do campo
        if (erro instanceof ErroApi && (erro.tipo === 'RA' || erro.tipo === 'PA')) erroCampo(formulario, erro);
        else await falhaDaApi(erro, 'Não foi possível iniciar o treino');
      }
    });

    sugerirNome();
    return formulario;
  }

  function lerFormulario(formulario) {
    const dados = new FormData(formulario);
    valores.modelo = dados.get('modelo');
    // Épocas do modo atual: do treino normal ou da execução de teste (o servidor sabe qual pela execucao_teste)
    valores.epocas = formulario.querySelector('#epocas').value;
    valores.early_stopping = formulario.querySelector('#early_stopping').checked;
    valores.paciencia = formulario.querySelector('#paciencia').value;
    valores.batch_size = formulario.querySelector('#batch_size').value;
    valores.datasets = dados.getAll('datasets');
    valores.execucao_teste = dados.get('execucao_teste') !== null;
    valores.execucao_teste_imagens = formulario.querySelector('#execucao_teste_imagens').value;
  }

  limpar(corpo, desenharFormulario());
  corpo.querySelector('#nome')?.focus();

  // A coluna da direita reserva a altura do modo mais alto (a execução de teste), para a seção não mudar
  // de tamanho e o botão "Iniciar o treino" não mudar de lugar ao marcar e desmarcar as opções
  const coluna = corpo.querySelector('.coluna-dinamica');
  function reservarAltura() {
    const campos = ['paciencia', 'epocas', 'execucao_teste_imagens'].map((c) => coluna.querySelector(`[data-campo="${c}"]`));
    const antes = campos.map((c) => c.hidden);
    coluna.style.minHeight = '';
    // Campos visíveis em cada modo: early stopping, treino sem early stopping e execução de teste
    const alturas = [[true, false, false], [false, true, false], [false, true, true]].map((visiveis) => {
      campos.forEach((c, i) => { c.hidden = !visiveis[i]; });
      return coluna.offsetHeight;
    });
    campos.forEach((c, i) => { c.hidden = antes[i]; });
    coluna.style.minHeight = `${Math.max(...alturas)}px`;
  }
  reservarAltura();
  // Em tela estreita as colunas empilham e a altura muda: mede de novo
  window.addEventListener('resize', reservarAltura);
  return { sair: () => window.removeEventListener('resize', reservarAltura) };
}

const MOTIVOS = {
  epocas: (p) => `o treino chegou ao número de épocas pedido (${p.epocas}).`,
  early_stopping: (p) => `o early stopping encerrou o treino porque o desempenho na validação não melhorou nas últimas ${p.paciencia} épocas.`,
  execucao_de_teste: (p) => `a execução de teste estava ligada e o treino chegou às ${p.execucao_teste_epocas ?? p.epocas} épocas dela.`,
};

export async function renderAcompanhar(main, { id }, _consulta, contexto) {
  let configuracao = await api.get(`/api/configuracoes/${enc(id)}`);
  const corpo = h('div', { 'aria-live': 'polite' });
  limpar(main, cabecalho(configuracao.nome, configuracao.descricao, h('a', { href: '#/treino/novo' }, '← Treinar uma configuração')), corpo);

  function graficos(historico, ligados) {
    if (!historico.length) return null;
    const epocas = historico.map((e) => e.epoca);
    const serie = (chave, onde) => historico.map((e) => (onde === 'treino' ? e.treino?.[chave] : e.validacao?.[chave]) ?? null);
    const temValidacao = historico.some((e) => e.validacao);
    const montar = (titulo, chave) => graficoDeLinhas({
      titulo, epocas,
      series: [
        { nome: 'Treino (linha contínua)', valores: serie(chave, 'treino'), cor: '#1d4ed8' },
        temValidacao ? { nome: 'Validação (linha tracejada)', valores: serie(chave, 'validacao'), cor: '#b45309', tracejada: true } : null,
      ].filter(Boolean),
    });

    const tabela = h('div', { class: 'tabela-rolagem' }, h('table', {},
      h('caption', { class: 'oculto-visual' }, 'Métricas de cada época'),
      h('thead', {}, h('tr', {}, h('th', {}, 'Época'), h('th', { class: 'numero' }, 'Loss (treino)'), h('th', { class: 'numero' }, 'Acurácia (treino)'),
        h('th', { class: 'numero' }, 'IoU médio (treino)'), h('th', { class: 'numero' }, 'Loss (validação)'), h('th', { class: 'numero' }, 'Acurácia (validação)'),
        h('th', { class: 'numero' }, 'IoU médio (validação)'))),
      h('tbody', {}, historico.slice().reverse().map((e) => h('tr', {},
        h('td', {}, e.epoca),
        h('td', { class: 'numero' }, formato.metrica(e.treino?.loss)), h('td', { class: 'numero' }, formato.metrica(e.treino?.acuracia)),
        h('td', { class: 'numero' }, formato.metrica(e.treino?.miou)), h('td', { class: 'numero' }, formato.metrica(e.validacao?.loss)),
        h('td', { class: 'numero' }, formato.metrica(e.validacao?.acuracia)), h('td', { class: 'numero' }, formato.metrica(e.validacao?.miou)))))));

    return h('div', { class: 'cartao' },
      h('h2', {}, 'Gráficos de treino e validação'),
      ligados ? h('div', { class: 'grade-2' },
        montar('Loss (quanto menor, melhor)', 'loss'),
        montar('Acurácia', 'acuracia'),
        montar('IoU médio', 'miou')) : h('p', { class: 'suave' }, 'A geração de gráficos está desligada nesta configuração; os valores estão na tabela.'),
      h('details', { open: !ligados }, h('summary', {}, 'Tabela das épocas'), tabela));
  }

  // O02.2: época, motivo do término, métricas e matriz de confusão, só depois da avaliação no conjunto de teste
  function resultado() {
    const treino = configuracao.treino;
    const teste = configuracao.teste;
    const motivo = treino.antes_da_interface
      ? h('p', {}, h('strong', {}, 'Treino concluído. '), 'Esta configuração foi treinada antes da interface; as épocas não foram registradas aqui.')
      : h('p', {}, h('strong', {}, `Treino concluído na época ${treino.epoca_final}: `), MOTIVOS[treino.motivo_termino]?.(configuracao.parametros) || '');
    const m = teste.metricas;

    return [
      mensagem('ok', motivo,
        treino.melhor_epoca ? h('p', {}, `Os pesos guardados são os da época ${treino.melhor_epoca}, a de melhor IoU médio na validação.`) : null,
        h('p', {}, `A ${configuracao.nome} está entre as configurações disponíveis e foi avaliada no conjunto de teste.`)),
      h('div', { class: 'cartao' },
        h('h2', {}, 'Resultado no ', 'conjunto de teste'),
        h('p', { class: 'pequeno suave' }, conjuntoTexto(teste.conjunto), '.'),
        h('table', { style: 'max-width:520px' }, h('tbody', {},
          h('tr', {}, h('th', {}, 'IoU da classe Trilha'), h('td', { class: 'numero' }, formato.metrica(m.iou_trilha))),
          h('tr', {}, h('th', {}, 'IoU médio'), h('td', { class: 'numero' }, formato.metrica(m.miou))),
          h('tr', {}, h('th', {}, 'Acurácia'), h('td', { class: 'numero' }, formato.metrica(m.acuracia))),
          h('tr', {}, h('th', {}, 'Tempo de inferência'), h('td', { class: 'numero' }, formato.ms(m.tempo_inferencia_ms))))),
        h('h3', { style: 'margin-top:1rem' }, 'Matriz de confusão'),
        tabelaMatriz(teste.matriz, configuracao.nome)),
      h('div', { class: 'linha' },
        h('a', { class: 'botao', href: `#/segmentar?configuracoes=${enc(configuracao.id)}` }, 'Comparar com outra configuração no vídeo'),
        h('a', { class: 'botao botao-secundario', href: '#/' }, 'Concluir por agora')),
    ];
  }

  // Estado da avaliação automática no conjunto de teste, depois do treino
  function estadoAvaliacao() {
    const avaliacao = configuracao.avaliacao || {};
    const tarefa = tarefaAvaliacao(contexto.estado, id);
    const valor = avaliacao.estado || (configuracao.teste ? 'concluída' : null);

    const linhas = [
      h('div', { class: 'linha-entre' }, h('h2', {}, 'Avaliação no conjunto de teste'),
        valor ? estado(valor) : h('span', { class: 'estado estado-fila' }, 'Sem avaliação')),
    ];
    if (valor === 'na fila') linhas.push(h('p', {}, 'Aguardando a vez: os processamentos rodam um de cada vez.'));
    if (valor === 'processando') {
      linhas.push(progresso(tarefa?.progresso.atual || 0, tarefa?.progresso.total || 0, tarefa?.progresso.texto || 'Avaliando no conjunto de teste'));
    }
    if (!valor) {
      linhas.push(h('p', {}, 'Esta configuração está sem avaliação no conjunto de teste atual. A avaliação é feita na tela ',
        h('a', { href: '#/datasets' }, 'Datasets'), '.'));
    }
    linhas.push(h('p', { class: 'suave' }, 'Métricas disponíveis após a avaliação no conjunto de teste.'));
    return h('div', { class: 'cartao' }, linhas);
  }

  // Ruptura "treino ou avaliação interrompidos" (RA): causa, etapa, configuração mantida, ajuste sugerido
  function interrompido() {
    const treino = configuracao.treino;
    const falhaTreino = treino.estado === 'falhou';
    const falha = falhaTreino ? treino : configuracao.avaliacao;
    const memoria = falha.causa === 'faltou memória no computador';
    const etapa = falhaTreino
      ? (treino.epoca ? `treino, na época ${treino.epoca}${treino.total ? ` de ${treino.total}` : ''}` : 'treino, antes da primeira época')
      : 'avaliação no conjunto de teste, depois do treino';
    const sugerido = treino.batch_size_sugerido || Math.max(1, Math.floor(configuracao.parametros.batch_size / 2));
    const reiniciavel = !falhaTreino || configuracao.origem === 'interface';

    const campo = h('input', { type: 'number', id: 'novo-batch', min: '1', step: '1', value: String(memoria ? sugerido : configuracao.parametros.batch_size) });
    const botao = h('button', { type: 'button', class: 'botao' }, 'Reiniciar com o ajuste');
    botao.addEventListener('click', async () => {
      botao.disabled = true;
      try {
        configuracao = falhaTreino
          ? await api.post(`/api/treino/${enc(id)}/reiniciar`, { batch_size: Number(campo.value) })
          : await api.post(`/api/configuracoes/${enc(id)}/avaliar`);
        anunciar(falhaTreino ? 'Treino reiniciado.' : 'Avaliação no conjunto de teste reiniciada.');
        await contexto.atualizarEstado();
        desenhar();
      } catch (erro) {
        botao.disabled = false;
        await falhaDaApi(erro, 'Não foi possível reiniciar');
      }
    });

    const ajuste = falhaTreino
      ? (memoria ? `reduzir o batch size para ${sugerido}.` : (falha.sugestao || 'reiniciar com os mesmos parâmetros.'))
      : (falha.sugestao || 'tentar a avaliação de novo.');

    return mensagem('falha',
      h('h2', {}, 'Treino ou avaliação interrompidos'),
      h('dl', { class: 'resumo' },
        h('dt', {}, 'Causa'), h('dd', {}, falha.causa),
        h('dt', {}, 'Etapa'), h('dd', {}, etapa),
        h('dt', {}, 'Configuração'), h('dd', {}, 'mantida, com os mesmos parâmetros'),
        h('dt', {}, 'Ajuste sugerido'), h('dd', {}, ajuste)),
      falha.tipo_falha === 'CE' && /dataset/i.test(`${falha.causa} ${falha.sugestao || ''}`)
        ? h('p', {}, 'A solução está fora desta tela: ', h('a', { href: '#/datasets' }, 'abra a tela Datasets'), '.') : null,
      reiniciavel ? h('div', { class: 'linha', style: 'margin-top:.6rem' },
        falhaTreino ? h('label', { for: 'novo-batch' }, 'Batch size') : null, falhaTreino ? campo : null, botao) : null);
  }

  function desenhar() {
    const treino = configuracao.treino || {};
    const avaliacao = configuracao.avaliacao || {};
    const partes = [];
    const treinoEmAndamento = treino.estado === 'na fila' || treino.estado === 'treinando';

    if (treinoEmAndamento) {
      partes.push(h('div', { class: 'cartao' },
        h('div', { class: 'linha-entre' }, h('h2', {}, 'Estado do treino'), estado(treino.estado)),
        treino.estado === 'na fila'
          ? h('p', {}, 'Aguardando a vez: os processamentos rodam um de cada vez. O treino começa quando o anterior terminar.')
          : progresso(treino.epoca || 0, treino.total || 0, treino.total
            ? `Treinando: época ${treino.epoca || 0} de ${treino.total}`
            : `Treinando: época ${treino.epoca || 0} (até o early stopping parar)`),
        h('p', { class: 'suave' }, 'Métricas disponíveis após a avaliação no conjunto de teste.')));
    } else if (treino.estado === 'falhou' || avaliacao.estado === 'falhou') {
      partes.push(interrompido());
    } else if (treino.estado === 'concluído' && configuracao.teste && avaliacao.estado !== 'na fila' && avaliacao.estado !== 'processando') {
      partes.push(...resultado());
    } else if (treino.estado === 'concluído') {
      partes.push(h('div', { class: 'cartao' },
        h('div', { class: 'linha-entre' }, h('h2', {}, 'Estado do treino'), estado('concluído')),
        treino.epoca_final ? h('p', {}, `As épocas terminaram (época ${treino.epoca_final}).`) : null),
      estadoAvaliacao());
    }

    partes.push(graficos(treino.historico || [], configuracao.parametros.graficos));
    limpar(corpo, partes);
  }

  desenhar();

  let ultimo = '';
  return {
    async atualizar(estadoGeral) {
      const emAndamento = ['na fila', 'treinando'].includes(configuracao.treino?.estado)
        || ['na fila', 'processando'].includes(configuracao.avaliacao?.estado);
      if (!emAndamento) return;
      configuracao = await api.get(`/api/configuracoes/${enc(id)}`);
      const tarefa = tarefaAvaliacao(estadoGeral, id);
      const chave = JSON.stringify([configuracao.treino.estado, configuracao.treino.epoca, configuracao.avaliacao?.estado, tarefa?.progresso.atual]);
      if (chave !== ultimo) {
        const antes = ultimo;
        ultimo = chave;
        desenhar();
        if (antes && configuracao.avaliacao?.estado === 'concluída') anunciar('Avaliação no conjunto de teste concluída. As métricas estão disponíveis.');
      }
    },
  };
}
