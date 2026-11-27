// O07.1 Entender um termo: o que o termo indica e o que ele não indica (acesso ubíquo).
// Os textos seguem o esquema de signos da Entrega 9, seção 4.

const SEGURANCA = 'Nenhuma métrica garante que um trajeto é seguro.';

export const TERMOS = {
  configuracao: {
    titulo: 'Configuração',
    indica: 'Um modelo (FCN ou DeepLabV3+) treinado com um conjunto de parâmetros de treino. É o que se treina, executa e compara.',
    nao: 'Não inclui os parâmetros internos do treino, que ficam fixos no sistema.',
  },
  conjunto_de_teste: {
    titulo: 'Conjunto de teste',
    indica: 'Parte dos datasets do TCC separada para teste: imagens com anotação de referência que não são usadas no treino. É nele que o IoU, a acurácia e a matriz de confusão são calculados.',
    nao: 'As métricas do conjunto de teste não valem para as imagens dos testes do Baja, que não têm anotação de referência.',
  },
  anotacao_de_referencia: {
    titulo: 'Anotação de referência',
    indica: 'Máscara feita à mão que indica a resposta certa. Só as imagens do conjunto de teste têm.',
    nao: 'Imagens novas de campo não têm anotação; por isso não há IoU nem acurácia para elas, e a avaliação é visual.',
  },
  iou: {
    titulo: 'IoU',
    indica: 'Quanto as regiões marcadas pela configuração coincidem com as regiões anotadas, para uma classe (Trilha ou Fora da trilha). Vai de 0 a 1: quanto mais perto de 1, mais elas coincidem.',
    nao: `Não mostra em que tipo de trecho a configuração erra. Só é calculado no conjunto de teste. ${SEGURANCA}`,
  },
  iou_medio: {
    titulo: 'IoU médio',
    indica: 'Compara as regiões que a configuração marcou como Trilha e Fora da trilha com as regiões anotadas no conjunto de teste: quanto mais perto de 1, mais elas coincidem. Indica o acerto geral.',
    nao: `Não mostra em que tipo de trecho a configuração erra. ${SEGURANCA}`,
  },
  iou_trilha: {
    titulo: 'IoU da classe Trilha',
    indica: 'Quanto a região que a configuração marcou como Trilha coincide com a trilha anotada no conjunto de teste, de 0 a 1.',
    nao: `Não diz se a trilha é transitável nem em que trechos a configuração erra. ${SEGURANCA}`,
  },
  iou_fundo: {
    titulo: 'IoU da classe Fora da trilha',
    indica: 'Quanto a região que a configuração marcou como Fora da trilha coincide com a região anotada como Fora da trilha, de 0 a 1.',
    nao: `Costuma ser alto porque a maior parte das imagens fica fora da trilha; sozinho, não mostra se a trilha foi bem reconhecida. ${SEGURANCA}`,
  },
  acuracia: {
    titulo: 'Acurácia',
    indica: 'Proporção dos pontos das imagens do conjunto de teste classificados corretamente, de 0 a 1.',
    nao: `Pode ser alta mesmo quando a trilha é pouco reconhecida, porque a maior parte da imagem é Fora da trilha. ${SEGURANCA}`,
  },
  tempo_inferencia: {
    titulo: 'Tempo de inferência',
    indica: 'Tempo médio para a configuração segmentar uma imagem do conjunto de teste.',
    nao: 'Depende do computador usado: a mesma configuração pode ser mais rápida ou mais lenta em outra máquina.',
  },
  matriz_confusao: {
    titulo: 'Matriz de confusão',
    indica: 'Quanto do que era Trilha foi marcado como Fora da trilha, e o contrário, no conjunto de teste. Mostra o tipo de erro de cada configuração.',
    nao: `Não mostra onde, na imagem, os erros acontecem. ${SEGURANCA}`,
  },
  valor_de_referencia: {
    titulo: 'Valor de referência',
    indica: 'Valor de comparação exibido junto de cada métrica. Neste sistema, é o valor da configuração em uso (a última executada), no conjunto de teste.',
    nao: 'Não é uma meta nem um mínimo aceitável: é só o ponto de partida para comparar.',
  },
  maior_valor: {
    titulo: 'Maior valor',
    indica: 'Destaca a configuração com o maior valor em cada métrica, para organizar a leitura.',
    nao: 'Não é uma recomendação do sistema: a escolha da configuração é de vocês.',
  },
  diferenca: {
    titulo: 'Diferença entre configurações',
    indica: 'Diferença calculada entre os valores de uma métrica de duas configurações avaliadas no mesmo conjunto de teste (ex.: +0,020 no IoU médio).',
    nao: 'O sistema não indica se a diferença é relevante: isso depende do critério de vocês.',
  },
  mascara: {
    titulo: 'Máscara',
    indica: 'A classificação de cada ponto da imagem em Trilha ou Fora da trilha, feita por uma configuração.',
    nao: 'Não indica se o trecho é seguro ou transitável.',
  },
  sobreposicao: {
    titulo: 'Sobreposição',
    indica: 'A máscara exibida por cima da imagem original: a Trilha aparece pintada, com contorno branco; o que fica Fora da trilha continua com a imagem original.',
    nao: 'A transparência só muda a visualização, não o resultado.',
  },
  transparencia: {
    titulo: 'Transparência',
    indica: 'Quanto da máscara aparece na sobreposição, de 0% (só a imagem) a 100% (só a cor da Trilha).',
    nao: 'Não altera a segmentação.',
  },
  regiao_ampliada: {
    titulo: 'Região ampliada',
    indica: 'A área da imagem que você ampliou. Na comparação, a mesma região fica ampliada em todas as configurações.',
    nao: 'Não altera a segmentação.',
  },
  legenda: {
    titulo: 'Legenda',
    indica: 'O nome e a cor de cada classe: Trilha e Fora da trilha. As cores são as mesmas em todas as telas.',
    nao: 'A classe descreve a classificação do modelo; não indica se o trecho é seguro.',
  },
  avaliacao_imagem: {
    titulo: 'Avaliação da imagem',
    indica: 'O seu julgamento sobre a segmentação de uma imagem: correta ou duvidosa. Uma imagem que continua duvidosa depois da comparação é chamada de imagem inconclusiva.',
    nao: 'Não muda a máscara nem as métricas.',
  },
  origem_problema: {
    titulo: 'Origem do problema',
    indica: 'Para imagens duvidosas: se o problema parece estar na imagem (captura, como câmera contra o sol) ou no modelo.',
    nao: 'É o seu julgamento; o sistema não verifica a origem.',
  },
  ciclo_de_testes: {
    titulo: 'Ciclo de testes',
    indica: 'O nome ou a data do teste de campo. Reúne as execuções e a recomendação da configuração para esse teste.',
    nao: 'Não é um conjunto de imagens anotadas e não tem métricas próprias.',
  },
  sessao: {
    titulo: 'Sessão',
    indica: 'Reúne as imagens enviadas, as configurações executadas sobre elas e os resultados da análise atual.',
    nao: 'Não é um histórico de análises.',
  },
  epocas: {
    titulo: 'Épocas',
    indica: 'Número máximo de vezes que o treino percorre os datasets de treino.',
    nao: 'Mais épocas não garantem um resultado melhor; o early stopping pode encerrar o treino antes.',
  },
  early_stopping: {
    titulo: 'Early stopping',
    indica: 'Encerra o treino antes do número de épocas quando o desempenho na validação para de melhorar.',
    nao: 'Não interrompe o treino por falha; ele só termina mais cedo quando não há melhora.',
  },
  paciencia: {
    titulo: 'Paciência',
    indica: 'Número de épocas sem melhora na validação até o early stopping encerrar o treino.',
    nao: 'Só vale com o early stopping ligado.',
  },
  execucao_de_teste: {
    titulo: 'Execução de teste',
    indica: 'Treino leve, com poucas imagens e poucas épocas, para conferir que o fluxo funciona num computador modesto.',
    nao: 'O modelo resultante não serve para comparar com as configurações do TCC.',
  },
  batch_size: {
    titulo: 'Batch size',
    indica: 'Quantas imagens o treino processa por vez. Valores maiores usam mais memória do computador.',
    nao: 'Se faltar memória, o treino para; reduzir o batch size costuma resolver.',
  },
  datasets_de_treino: {
    titulo: 'Datasets de treino',
    indica: 'Conjuntos de imagens anotadas usados no treino: Freiburg Forest, Synthetic Offroad e CaSSeD.',
    nao: 'O conjunto de teste é separado e não é usado no treino.',
  },
  geracao_de_graficos: {
    titulo: 'Geração de gráficos',
    indica: 'Define se o treino gera os gráficos de treino e validação.',
    nao: 'A tabela das épocas aparece sempre, com ou sem gráficos.',
  },
  dataset_montado: {
    titulo: 'Dataset montado',
    indica: 'A cópia dos datasets brutos usada no treino e no teste. Montar ou remontar o dataset define as imagens de treino e o conjunto de teste atual.',
    nao: 'Os dados brutos (pasta raw/) não são apagados ao remontar.',
  },
  avaliacao_no_conjunto_de_teste: {
    titulo: 'Avaliação no conjunto de teste',
    indica: 'O cálculo das métricas da configuração (IoU, acurácia, tempo de inferência e matriz de confusão) no conjunto de teste atual. Ao fim de um treino, o sistema avalia a configuração automaticamente.',
    nao: 'Uma configuração sem avaliação no conjunto de teste atual não entra na comparação de desempenho.',
  },
  estado: {
    titulo: 'Estado',
    indica: 'Em que ponto está um processamento (treino, avaliação, montagem do dataset ou execução): na fila, processando (ou treinando), concluído ou falhou. Os processamentos rodam um de cada vez.',
    nao: 'Na fila não é falha: o processamento começa quando o anterior terminar.',
  },
  graficos_treino: {
    titulo: 'Gráficos de treino e validação',
    indica: 'A evolução do treino a cada época: loss (erro do treino, quanto menor melhor), acurácia e IoU médio, no treino e na validação.',
    nao: 'Os valores do treino e da validação não são as métricas do conjunto de teste.',
  },
};

let origem = null;

export function abrirTermo(chave, botaoDeOrigem) {
  const painel = document.getElementById('painel-termo');
  const corpo = document.getElementById('painel-termo-corpo');
  origem = botaoDeOrigem || document.activeElement;
  corpo.replaceChildren();

  if (chave && TERMOS[chave]) {
    const termo = TERMOS[chave];
    corpo.append(
      Object.assign(document.createElement('h3'), { textContent: termo.titulo }),
      definicao('O que indica', termo.indica),
      definicao('O que não indica', termo.nao),
    );
  } else {
    corpo.append(Object.assign(document.createElement('p'), { textContent: 'Escolha um termo:' }));
  }

  const lista = document.createElement('ul');
  lista.className = 'lista-termos';
  for (const [chaveTermo, termo] of Object.entries(TERMOS)) {
    const item = document.createElement('li');
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'botao botao-secundario botao-pequeno';
    botao.textContent = termo.titulo;
    botao.addEventListener('click', () => abrirTermo(chaveTermo, origem));
    if (chaveTermo === chave) botao.setAttribute('aria-current', 'true');
    item.append(botao);
    lista.append(item);
  }
  corpo.append(Object.assign(document.createElement('h3'), { textContent: 'Outros termos' }), lista);

  painel.hidden = false;
  painel.scrollTop = 0;
  // Foco no título: a leitura começa pelo termo, e Tab leva aos outros termos e ao "Voltar"
  document.getElementById('painel-termo-titulo').focus();
}

function definicao(titulo, texto) {
  const dl = document.createElement('dl');
  const dt = document.createElement('dt');
  dt.textContent = titulo;
  const dd = document.createElement('dd');
  dd.textContent = texto;
  dl.append(dt, dd);
  return dl;
}

export function fecharTermo() {
  document.getElementById('painel-termo').hidden = true;
  if (origem && document.body.contains(origem)) origem.focus();
  origem = null;
}


let popover = null;

export function fecharExplicacao() {
  if (!popover) return;
  const { elemento, botao, aoFechar } = popover;
  elemento.remove();
  document.removeEventListener('pointerdown', aoFechar, true);
  popover = null;
  if (botao && document.body.contains(botao)) {
    botao.setAttribute('aria-expanded', 'false');
    botao.focus();
  }
}

export function abrirExplicacao(chave, botao) {
  const mesmo = popover && popover.botao === botao;
  fecharExplicacao();
  if (mesmo || !TERMOS[chave]) return;

  const termo = TERMOS[chave];
  const id = `explicacao-${chave}`;
  const elemento = document.createElement('div');
  elemento.className = 'popover-termo';
  elemento.id = id;
  elemento.setAttribute('role', 'dialog');
  elemento.setAttribute('aria-modal', 'false');
  elemento.setAttribute('aria-labelledby', `${id}-titulo`);

  const titulo = Object.assign(document.createElement('h2'), { id: `${id}-titulo`, textContent: termo.titulo, tabIndex: -1 });
  const fechar = Object.assign(document.createElement('button'), { type: 'button', className: 'botao botao-secundario botao-pequeno', textContent: 'Fechar' });
  fechar.addEventListener('click', fecharExplicacao);
  elemento.append(titulo, definicao('O que indica', termo.indica), definicao('O que não indica', termo.nao), fechar);
  elemento.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') { evento.stopPropagation(); fecharExplicacao(); }
  });

  document.body.append(elemento);
  const caixa = botao.getBoundingClientRect();
  const largura = Math.min(360, window.innerWidth - 24);
  elemento.style.width = `${largura}px`;
  elemento.style.left = `${Math.max(12, Math.min(caixa.left + window.scrollX, window.scrollX + window.innerWidth - largura - 12))}px`;
  elemento.style.top = `${caixa.bottom + window.scrollY + 8}px`;

  // Clique fora fecha sem tirar a pessoa da tela
  const aoFechar = (evento) => {
    if (!elemento.contains(evento.target) && evento.target !== botao) fecharExplicacao();
  };
  document.addEventListener('pointerdown', aoFechar, true);
  popover = { elemento, botao, aoFechar };
  botao.setAttribute('aria-expanded', 'true');
  botao.setAttribute('aria-controls', id);
  titulo.focus({ preventScroll: true });
}
