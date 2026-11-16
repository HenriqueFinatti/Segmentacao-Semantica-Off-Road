// M03: O01.1 Escolher o modelo e os parâmetros · O01.2 Nomear a configuração ·
// O02.1 Acompanhar o treino (ruptura "treino interrompido") · O02.2 Conferir o resultado do treino.
import { api, enc, ErroApi } from '../api.js';
import { h, limpar, cabecalho, mensagem, estado, progresso, termo, erroCampo, falhaDaApi, anunciar, formato, conjuntoTexto } from '../ui.js';
import { graficoDeLinhas } from '../graficos.js';
import { tabelaMatriz } from './desempenho.js';

export async function renderNovo(main, _p, _consulta, contexto) {
  const padroes = await api.get('/api/treino/padroes');
  const valores = { ...padroes.padrao, modelo: 'deeplabv3+', nome: '' };
  let passo = 1;

  const titulo = cabecalho('Treinar uma configuração',
    'Defina o modelo e os parâmetros de treino. Os valores já preenchidos são os padrões do TCC.');
  const corpo = h('div', {});
  limpar(main, titulo, corpo);

  function passos() {
    return h('ol', { class: 'passos', 'aria-label': 'Etapas' },
      h('li', { 'aria-current': passo === 1 ? 'step' : null }, '1. Escolher o modelo e os parâmetros'),
      h('li', { 'aria-current': passo === 2 ? 'step' : null }, '2. Nomear a configuração'));
  }

  function numero(campo, rotulo, chaveTermo, ajuda, extra = {}) {
    return h('div', { class: 'campo', 'data-campo': campo },
      h('label', { for: campo }, termo(rotulo, chaveTermo)),
      ajuda ? h('span', { class: 'ajuda', id: `ajuda-${campo}` }, ajuda) : null,
      h('input', { type: 'number', id: campo, name: campo, min: '1', step: '1', value: String(valores[campo]), inputmode: 'numeric',
        'aria-describedby': ajuda ? `ajuda-${campo}` : null, ...extra }));
  }

  function desenharPasso1() {
    const formulario = h('form', { class: 'cartao', novalidate: true },
      h('fieldset', { 'data-campo': 'modelo' }, h('legend', {}, 'Modelo'),
        padroes.modelos.map((m) => h('label', { class: 'opcao' },
          h('input', { type: 'radio', name: 'modelo', value: m.id, checked: valores.modelo === m.id }), m.nome))),
      h('div', { class: 'grade-2' },
        h('div', {},
          numero('epocas', 'Épocas', 'epocas', 'Número máximo de épocas. Padrão do TCC: 200.'),
          h('label', { class: 'opcao' }, h('input', { type: 'checkbox', name: 'early_stopping', checked: valores.early_stopping }),
            termo('Early stopping', 'early_stopping')),
          numero('paciencia', 'Paciência', 'paciencia', 'Épocas sem melhora na validação até encerrar. Só vale com o early stopping ligado.',
            { disabled: !valores.early_stopping }),
          numero('batch_size', 'Batch size', 'batch_size', 'Valores maiores exigem mais memória do computador.')),
        h('div', {},
          h('fieldset', { 'data-campo': 'datasets' }, h('legend', {}, termo('Datasets de treino', 'datasets_de_treino')),
            padroes.datasets.map((d) => {
              const vazio = d.imagens_treino === 0;
              return h('label', { class: `opcao ${vazio ? 'desabilitada' : ''}` },
                h('input', { type: 'checkbox', name: 'datasets', value: d.id, checked: valores.datasets.includes(d.id) && !vazio, disabled: vazio }),
                h('span', {}, d.nome, h('span', { class: 'pequeno suave', style: 'display:block' },
                  vazio ? 'Não está no dataset montado (veja a tela Datasets).' : `${formato.inteiro(d.imagens_treino)} imagens de treino no dataset montado`)));
            })),
          h('label', { class: 'opcao' }, h('input', { type: 'checkbox', name: 'graficos', checked: valores.graficos }),
            termo('Geração de gráficos', 'geracao_de_graficos')))),
      h('p', { class: 'pequeno suave' }, 'Os parâmetros internos do treino (taxa de aprendizado, tamanho da imagem e outros) são fixos do TCC.'),
      h('div', { class: 'linha' }, h('button', { type: 'submit', class: 'botao' }, 'Continuar')));

    const caixaEarly = formulario.querySelector('input[name="early_stopping"]');
    caixaEarly.addEventListener('change', () => { formulario.querySelector('#paciencia').disabled = !caixaEarly.checked; });

    formulario.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      lerPasso1(formulario);
      try {
        await api.post('/api/treino/validar', valores);
        const sugestao = await api.get(`/api/treino/nome-sugerido?modelo=${enc(valores.modelo)}&epocas=${enc(valores.epocas)}`);
        valores.nome = sugestao.nome;
        passo = 2;
        desenhar();
      } catch (erro) {
        if (erro instanceof ErroApi && erro.tipo === 'PA') erroCampo(formulario, erro);
        else await falhaDaApi(erro);
      }
    });
    return formulario;
  }

  function lerPasso1(formulario) {
    const dados = new FormData(formulario);
    valores.modelo = dados.get('modelo');
    valores.epocas = formulario.querySelector('#epocas').value;
    valores.early_stopping = dados.get('early_stopping') !== null;
    valores.paciencia = formulario.querySelector('#paciencia').value;
    valores.batch_size = formulario.querySelector('#batch_size').value;
    valores.datasets = dados.getAll('datasets');
    valores.graficos = dados.get('graficos') !== null;
  }

  function desenharPasso2() {
    const nomeModelo = padroes.modelos.find((m) => m.id === valores.modelo)?.nome;
    const datasets = padroes.datasets.filter((d) => valores.datasets.includes(d.id)).map((d) => d.nome).join(', ');
    const campoNome = h('input', { type: 'text', id: 'nome', value: valores.nome, autocomplete: 'off', 'aria-describedby': 'ajuda-nome' });

    const formulario = h('form', { class: 'cartao', novalidate: true },
      h('dl', { class: 'resumo' },
        h('dt', {}, 'Modelo'), h('dd', {}, nomeModelo),
        h('dt', {}, 'Épocas'), h('dd', {}, valores.epocas),
        h('dt', {}, 'Early stopping'), h('dd', {}, valores.early_stopping ? `sim, paciência ${valores.paciencia}` : 'não'),
        h('dt', {}, 'Batch size'), h('dd', {}, valores.batch_size),
        h('dt', {}, 'Datasets de treino'), h('dd', {}, datasets),
        h('dt', {}, 'Geração de gráficos'), h('dd', {}, valores.graficos ? 'sim' : 'não')),
      h('div', { class: 'campo', 'data-campo': 'nome', style: 'margin-top:1rem' },
        h('label', { for: 'nome' }, 'Nome da configuração'),
        h('span', { class: 'ajuda', id: 'ajuda-nome' }, `Sugiro "${valores.nome}", a partir do modelo e das épocas. O nome identifica a configuração para toda a equipe.`),
        campoNome),
      h('div', { class: 'linha' },
        h('button', { type: 'button', class: 'botao botao-secundario', onclick: () => { valores.nome = campoNome.value; passo = 1; desenhar(); } }, 'Voltar aos parâmetros'),
        h('button', { type: 'submit', class: 'botao' }, 'Iniciar o treino')));

    formulario.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      valores.nome = campoNome.value.trim();
      try {
        const configuracao = await api.post('/api/treino', valores);
        anunciar(`Treino iniciado com a ${configuracao.nome}.`);
        await contexto.atualizarEstado();
        contexto.navegar(`#/treino/${enc(configuracao.id)}?iniciado=1`);
      } catch (erro) {
        if (erro instanceof ErroApi && (erro.tipo === 'RA' || erro.tipo === 'PA')) {
          erroCampo(formulario, erro);
          // Recuperação apoiada: nome repetido, com outra sugestão
          if (erro.dados?.sugestao) {
            formulario.querySelector('[data-campo="nome"]').append(h('button', {
              type: 'button', class: 'botao-link', onclick: () => { campoNome.value = erro.dados.sugestao; campoNome.focus(); },
            }, `Usar "${erro.dados.sugestao}"`));
          }
        } else {
          await falhaDaApi(erro, 'Não foi possível iniciar o treino');
        }
      }
    });
    return formulario;
  }

  function desenhar() {
    limpar(corpo, passos(), passo === 1 ? desenharPasso1() : desenharPasso2());
    corpo.querySelector('input:not([disabled])')?.focus();
  }

  desenhar();
}

const MOTIVOS = {
  epocas: (t, p) => `o treino chegou ao número de épocas pedido (${p.epocas}).`,
  early_stopping: (t, p) => `o early stopping encerrou o treino porque o desempenho na validação não melhorou nas últimas ${p.paciencia} épocas.`,
  execucao_de_teste: () => 'a execução de teste está ligada no settings.json, que limita o número de épocas.',
};

export async function renderAcompanhar(main, { id }, consulta) {
  let configuracao = await api.get(`/api/configuracoes/${enc(id)}`);
  const corpo = h('div', {});
  limpar(main, cabecalho(configuracao.nome, configuracao.descricao, h('a', { href: '#/treino/novo' }, '← Treinar uma configuração')), corpo);
  const iniciado = consulta.get('iniciado') === '1';

  function graficos(historico, ligados) {
    if (!historico.length) return null;
    const epocas = historico.map((e) => e.epoca);
    const serie = (chave, onde) => historico.map((e) => (onde === 'treino' ? e.treino?.[chave] : e.validacao?.[chave]) ?? null);
    const temValidacao = historico.some((e) => e.validacao);
    const montar = (titulo, chave, rotuloY) => graficoDeLinhas({
      titulo, epocas, rotuloY,
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
      h('h2', {}, termo('Gráficos de treino e validação', 'graficos_treino')),
      ligados ? h('div', { class: 'grade-2' },
        montar('Loss (quanto menor, melhor)', 'loss', 'Loss'),
        montar('Acurácia', 'acuracia', 'Acurácia'),
        montar('IoU médio', 'miou', 'IoU médio')) : h('p', { class: 'suave' }, 'A geração de gráficos está desligada nesta configuração; os valores estão na tabela.'),
      h('details', { open: !ligados }, h('summary', {}, 'Tabela das épocas'), tabela));
  }

  function resultado(configuracao) {
    const treino = configuracao.treino;
    const p = configuracao.parametros;
    const teste = configuracao.teste;
    const partes = [];

    if (treino.antes_da_interface) {
      partes.push(mensagem('ok', h('p', {}, h('strong', {}, 'Treino concluído. '),
        'Esta configuração foi treinada antes da interface; as épocas não foram registradas aqui.')));
    } else {
      const motivo = MOTIVOS[treino.motivo_termino]?.(treino, p) || '';
      partes.push(mensagem('ok',
        h('p', {}, h('strong', {}, `Treino concluído na época ${treino.epoca_final}: `), motivo),
        treino.melhor_epoca ? h('p', {}, `Os pesos guardados são os da época ${treino.melhor_epoca}, a de melhor IoU médio na validação.`) : null,
        h('p', {}, `A ${configuracao.nome} está entre as configurações disponíveis.`)));
    }

    if (teste) {
      const m = teste.metricas;
      partes.push(h('div', { class: 'cartao' },
        h('h2', {}, 'Resultado no ', termo('conjunto de teste', 'conjunto_de_teste')),
        h('p', { class: 'pequeno suave' }, conjuntoTexto(teste.conjunto), '.'),
        h('table', { style: 'max-width:520px' }, h('tbody', {},
          h('tr', {}, h('th', {}, termo('IoU da classe Trilha', 'iou_trilha')), h('td', { class: 'numero' }, formato.metrica(m.iou_trilha))),
          h('tr', {}, h('th', {}, termo('IoU médio', 'iou_medio')), h('td', { class: 'numero' }, formato.metrica(m.miou))),
          h('tr', {}, h('th', {}, termo('Acurácia', 'acuracia')), h('td', { class: 'numero' }, formato.metrica(m.acuracia))),
          h('tr', {}, h('th', {}, termo('Tempo de inferência', 'tempo_inferencia')), h('td', { class: 'numero' }, formato.ms(m.tempo_inferencia_ms))))),
        h('h3', { style: 'margin-top:1rem' }, termo('Matriz de confusão', 'matriz_confusao')),
        tabelaMatriz(teste.matriz, configuracao.nome)));
    } else {
      partes.push(mensagem('alerta', h('p', {}, 'Não há conjunto de teste montado, por isso esta configuração está sem métricas.'),
        h('p', {}, 'Monte o dataset e avalie a configuração na tela ', h('a', { href: '#/datasets' }, 'Datasets'), '.')));
    }

    partes.push(h('div', { class: 'linha' },
      h('a', { class: 'botao', href: `#/segmentar?configuracoes=${enc(configuracao.id)}` }, 'Comparar com outra configuração nestes quadros'),
      h('a', { class: 'botao botao-secundario', href: `#/desempenho` }, 'Comparar o desempenho')));
    return partes;
  }

  function interrompido() {
    const treino = configuracao.treino;
    const memoria = treino.causa === 'faltou memória no computador';
    const sugerido = treino.batch_size_sugerido || Math.max(1, Math.floor(configuracao.parametros.batch_size / 2));
    const campo = h('input', { type: 'number', id: 'novo-batch', min: '1', step: '1', value: String(memoria ? sugerido : configuracao.parametros.batch_size) });
    const botao = h('button', { type: 'button', class: 'botao' }, memoria ? 'Reiniciar com o ajuste' : 'Reiniciar o treino');

    botao.addEventListener('click', async () => {
      try {
        configuracao = await api.post(`/api/treino/${enc(id)}/reiniciar`, { batch_size: Number(campo.value) });
        anunciar('Treino reiniciado.');
        desenhar();
      } catch (erro) {
        await falhaDaApi(erro, 'Não foi possível reiniciar');
      }
    });

    const parou = treino.epoca ? `o treino parou na época ${treino.epoca}` : 'o treino parou antes da primeira época';
    return mensagem('falha',
      h('h2', {}, 'Treino interrompido'),
      h('p', {}, h('strong', {}, 'Falhou: '), `${parou} porque ${treino.causa}. A configuração foi mantida.`),
      treino.sugestao ? h('p', {}, treino.sugestao, memoria ? ` Quer reiniciar com batch size ${sugerido}?` : '') : null,
      treino.tipo_falha === 'CE' && /dataset/i.test(treino.causa + (treino.sugestao || '')) ? h('p', {}, h('a', { href: '#/datasets' }, 'Abrir a tela Datasets')) : null,
      configuracao.origem === 'interface' ? h('div', { class: 'linha' },
        h('label', { for: 'novo-batch', class: 'rotulo' }, termo('Batch size', 'batch_size')), campo, botao) : null);
  }

  function desenhar() {
    const treino = configuracao.treino || {};
    const partes = [];

    if (treino.estado === 'na fila') {
      partes.push(mensagem('info', h('p', {}, estado('na fila'), ' Aguardando: há outra tarefa em execução. O treino começa quando ela terminar.')));
    } else if (treino.estado === 'treinando') {
      const avaliando = treino.etapa === 'Avaliando no conjunto de teste';
      partes.push(h('div', { class: 'cartao' },
        h('div', { class: 'linha-entre' }, h('h2', {}, 'Estado do treino'), estado('treinando')),
        avaliando ? h('p', {}, 'As épocas terminaram. Avaliando a configuração no conjunto de teste…')
          : progresso(treino.epoca || 0, treino.total || 0, `Treinando: época ${treino.epoca || 0} de ${treino.total || '?'}`),
        h('p', { class: 'pequeno suave' }, 'Você pode sair; o estado do treino fica disponível quando voltar, pelo botão "Em que ponto está o treino?" no topo. '
          + 'O treino só continua enquanto o programa da interface estiver aberto.')));
    } else if (treino.estado === 'falhou') {
      partes.push(interrompido());
    } else if (treino.estado === 'concluído') {
      partes.push(...resultado(configuracao));
    }

    if (iniciado && treino.estado !== 'concluído' && treino.estado !== 'falhou') {
      partes.unshift(mensagem('ok', h('p', {}, h('strong', {}, 'Treino iniciado '), `com a ${configuracao.nome}. Você pode sair; o estado do treino fica disponível quando voltar.`)));
    }

    partes.push(graficos(treino.historico || [], configuracao.parametros.graficos));
    limpar(corpo, partes);
  }

  desenhar();

  let ultimo = '';
  return {
    async atualizar() {
      if (!['na fila', 'treinando'].includes(configuracao.treino?.estado)) return;
      configuracao = await api.get(`/api/configuracoes/${enc(id)}`);
      const chave = JSON.stringify([configuracao.treino.estado, configuracao.treino.epoca, configuracao.treino.etapa]);
      if (chave !== ultimo) { ultimo = chave; desenhar(); }
    },
  };
}
