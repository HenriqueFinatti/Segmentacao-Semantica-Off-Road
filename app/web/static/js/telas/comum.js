// Peças repetidas entre telas: escolha de configurações, métricas resumidas e endereços dos arquivos da sessão.
import { h, formato, conjuntoTexto } from '../ui.js';

export function metricasCurtas(teste) {
  if (!teste) return h('span', { class: 'suave' }, 'Sem métricas no conjunto de teste.');
  const m = teste.metricas;
  return h('span', {}, `No conjunto de teste: IoU médio ${formato.metrica(m.miou)} · IoU da classe Trilha ${formato.metrica(m.iou_trilha)} · `
    + `acurácia ${formato.metrica(m.acuracia)}`);
}

/**
 * Lista de configurações para escolher (O03.1 e O06.1).
 * extras(config) devolve texto adicional por configuração.
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
        h('span', { class: 'nome' }, configuracao.nome),
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

export function urlSobreposicao(sessaoId, configuracaoId, nome) {
  return `/api/sessoes/${encodeURIComponent(sessaoId)}/sobreposicoes/${encodeURIComponent(configuracaoId)}/${encodeURIComponent(nome)}`;
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

// Imagens com resultado em pelo menos uma configuração (as deixadas de fora não aparecem nos resultados)
export function imagensComResultado(sessao) {
  const execucoes = Object.values(sessao.execucoes);
  return sessao.imagens.filter((imagem) => execucoes.some((e) => (e.concluidas || []).includes(imagem.nome)));
}
