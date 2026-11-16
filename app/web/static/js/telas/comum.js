// Peças repetidas entre telas: escolha de configurações, métricas resumidas e avaliações.
import { h, formato, situacao, icone, conjuntoTexto } from '../ui.js';

export function metricasCurtas(teste) {
  if (!teste) return h('span', { class: 'suave' }, 'Sem métricas no conjunto de teste.');
  const m = teste.metricas;
  return h('span', {}, `No conjunto de teste: IoU médio ${formato.metrica(m.miou)} · IoU da classe Trilha ${formato.metrica(m.iou_trilha)} · `
    + `acurácia ${formato.metrica(m.acuracia)}`);
}

/**
 * Lista de configurações para escolher (O03.1, O05.1 e O06.1).
 * extras(config) devolve texto adicional por configuração (ex.: "já executada nestas imagens").
 */
export function seletorDeConfiguracoes(configuracoes, { nome, multiplo = true, selecionadas = [], extras, rotulo } = {}) {
  const grupo = h('div', { class: 'lista-configuracoes', role: multiplo ? 'group' : 'radiogroup', 'aria-label': rotulo || 'Configurações' });

  for (const configuracao of configuracoes) {
    const id = `${nome}-${configuracao.id}`;
    const entrada = h('input', {
      type: multiplo ? 'checkbox' : 'radio', name: nome, value: configuracao.id, id,
      checked: selecionadas.includes(configuracao.id),
    });
    grupo.append(h('label', { class: 'item-configuracao', for: id },
      entrada,
      h('span', {},
        h('span', { class: 'nome' }, configuracao.nome), situacao(configuracao.situacao),
        h('span', { class: 'descricao', style: 'display:block' }, configuracao.descricao),
        h('span', { class: 'metricas-curtas', style: 'display:block' }, metricasCurtas(configuracao.teste)),
        configuracao.teste ? h('span', { class: 'pequeno suave', style: 'display:block' }, conjuntoTexto(configuracao.teste.conjunto)) : null,
        extras ? extras(configuracao) : null)));
  }

  return {
    elemento: grupo,
    valores: () => [...grupo.querySelectorAll('input:checked')].map((entrada) => entrada.value),
  };
}

export function marcadorAvaliacao(avaliacao) {
  if (!avaliacao) return h('span', { class: 'marcador marcador-sem' }, icone('sem'), 'sem avaliação');
  if (avaliacao.avaliacao === 'correta') return h('span', { class: 'marcador marcador-correta' }, icone('ok'), 'correta');
  return h('span', { class: 'marcador marcador-duvidosa' }, icone('alerta'),
    `duvidosa${avaliacao.origem_problema ? ` · ${avaliacao.origem_problema === 'modelo' ? 'problema no modelo' : 'problema na imagem (captura)'}` : ''}`);
}

export function textoAvaliacao(avaliacao) {
  if (!avaliacao) return 'sem avaliação';
  if (avaliacao.avaliacao === 'correta') return 'correta';
  if (!avaliacao.origem_problema) return 'duvidosa';
  return `duvidosa, ${avaliacao.origem_problema === 'modelo' ? 'problema no modelo' : 'problema na imagem (captura)'}`;
}

export function rotuloImagem(imagem) {
  if (imagem.origem === 'quadro') return `Quadro ${imagem.quadro} do vídeo ${imagem.video}`;
  return imagem.nome_original || imagem.nome;
}

export function tarefaDe(estado, alvo) {
  return (estado?.tarefas || []).find((tarefa) => Object.entries(alvo).every(([chave, valor]) => tarefa.alvo?.[chave] === valor));
}

export function urlImagem(sessaoId, nome) {
  return `/api/sessoes/${encodeURIComponent(sessaoId)}/imagens/${encodeURIComponent(nome)}`;
}

export function urlMascara(sessaoId, configuracaoId, nome) {
  return `/api/sessoes/${encodeURIComponent(sessaoId)}/mascaras/${encodeURIComponent(configuracaoId)}/${encodeURIComponent(nome)}`;
}

// Execuções concluídas da sessão (com resultado para mostrar)
export function configuracoesExecutadas(sessao) {
  return Object.entries(sessao.execucoes)
    .filter(([, execucao]) => (execucao.concluidas || []).length > 0)
    .map(([id]) => ({ id, nome: sessao.configuracoes[id]?.nome || id }));
}

export function temMascara(sessao, configuracaoId, nome) {
  return (sessao.execucoes[configuracaoId]?.concluidas || []).includes(nome);
}

// Imagens com resultado em pelo menos uma configuração (as deixadas de fora não entram na avaliação)
export function imagensComResultado(sessao) {
  const execucoes = Object.values(sessao.execucoes);
  return sessao.imagens.filter((imagem) => execucoes.some((e) => (e.concluidas || []).includes(imagem.nome)));
}
