// Lista de todos os treinos (concluídos, interrompidos, na fila e em andamento).
// Cada item abre a tela de acompanhamento daquele treino (#/treino/:id).
import { api, enc } from '../api.js';
import { h, limpar, cabecalho, mensagem, estado, formato } from '../ui.js';
import { metricasCurtas } from './comum.js';

const emAndamento = (c) => ['na fila', 'treinando'].includes(c.treino?.estado)
  || ['na fila', 'processando'].includes(c.avaliacao?.estado);

function duracao(segundos) {
  if (segundos === null || segundos === undefined) return null;
  const total = Math.round(segundos);
  const horas = Math.floor(total / 3600);
  const minutos = Math.floor((total % 3600) / 60);
  if (horas) return `${horas} h ${minutos} min`;
  if (minutos) return `${minutos} min`;
  return `${total} s`;
}

// Estado geral do treino e da avaliação no conjunto de teste, num selo só
function seloEstado(c) {
  const treino = c.treino || {};
  const avaliacao = c.avaliacao?.estado;
  if (treino.estado === 'na fila') return estado('na fila', 'Treino na fila');
  if (treino.estado === 'treinando') return estado('treinando', 'Treinando');
  if (treino.estado === 'falhou') return estado('falhou', 'Treino interrompido');
  if (avaliacao === 'falhou') return estado('falhou', 'Avaliação interrompida');
  if (avaliacao === 'na fila') return estado('na fila', 'Avaliação na fila');
  if (avaliacao === 'processando') return estado('processando', 'Avaliando no conjunto de teste');
  if (c.teste) return estado('concluído', 'Concluído');
  return estado('concluído', 'Treino concluído, sem avaliação');
}

// Linha de detalhes: quando começou, em que época está ou terminou e quanto tempo levou
function detalhes(c) {
  const treino = c.treino || {};
  const partes = [];
  if (treino.antes_da_interface) partes.push('Treinado antes da interface');
  else partes.push(`Iniciado em ${formato.data(treino.iniciado_em || c.criada_em)}`);

  if (treino.estado === 'treinando') {
    partes.push(treino.total ? `época ${treino.epoca || 0} de ${treino.total}` : `época ${treino.epoca || 0} (até o early stopping parar)`);
  } else if (treino.estado === 'falhou') {
    partes.push(treino.epoca ? `parou na época ${treino.epoca}` : 'parou antes da primeira época');
  } else if (treino.estado === 'concluído' && treino.epoca_final) {
    partes.push(`${treino.epoca_final} épocas`);
    if (treino.melhor_epoca) partes.push(`melhor época ${treino.melhor_epoca}`);
    const tempo = duracao(treino.tempo_total_s);
    if (tempo) partes.push(`duração ${tempo}`);
  }
  return partes.join(' · ');
}

function item(c) {
  return h('li', {},
    h('a', { class: 'item-lista', href: `#/treino/${enc(c.id)}` },
      h('span', { class: 'item-lista-cabeca' },
        h('span', { class: 'nome' }, c.nome),
        seloEstado(c)),
      h('span', { class: 'descricao' }, c.descricao),
      h('span', { class: 'pequeno' }, detalhes(c)),
      h('span', { class: 'metricas-curtas' }, metricasCurtas(c.teste))));
}

export async function render(main, _p, _consulta, _contexto) {
  let configuracoes = await api.get('/api/configuracoes');
  const corpo = h('div', {});
  limpar(main, cabecalho('Treinamentos',
    'Todos os treinos, os concluídos e os que estão em andamento. Abra um para ver o estado do treino, os gráficos e o resultado no conjunto de teste.'),
  corpo);

  function desenhar() {
    if (!configuracoes.length) {
      limpar(corpo, mensagem('neutra', h('p', {}, 'Ainda não há treinos.'),
        h('p', {}, h('a', { href: '#/treino/novo' }, 'Treinar uma configuração'))));
      return;
    }
    const andamento = configuracoes.filter(emAndamento);
    const demais = configuracoes.filter((c) => !emAndamento(c));
    const secao = (titulo, lista) => (lista.length ? h('section', { class: 'cartao', 'aria-label': titulo },
      h('h2', {}, `${titulo} (${lista.length})`),
      h('ul', { class: 'lista-itens' }, lista.map(item))) : null);
    limpar(corpo,
      secao('Em andamento', andamento),
      secao('Concluídos e interrompidos', demais),
      h('div', { class: 'linha' }, h('a', { class: 'botao', href: '#/treino/novo' }, 'Treinar uma configuração')));
  }

  desenhar();

  let ultimo = JSON.stringify(configuracoes);
  return {
    async atualizar(estadoGeral) {
      // Só busca a lista de novo quando há algo rodando (na lista ou na fila de tarefas)
      if (!configuracoes.some(emAndamento) && !(estadoGeral?.tarefas || []).length) return;
      configuracoes = await api.get('/api/configuracoes');
      const chave = JSON.stringify(configuracoes);
      if (chave === ultimo) return;
      ultimo = chave;
      desenhar();
    },
  };
}
