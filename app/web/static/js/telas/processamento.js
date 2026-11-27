// O03.2 Acompanhar o processamento (cena reusada pelo M01 e pelo M03).
// Estado de cada configuração na fila; ruptura "falha na execução" com "tentar de novo" ou "deixar de fora".
import { api, enc } from '../api.js';
import { h, limpar, cabecalho, mensagem, estado, progresso, falhaDaApi, anunciar } from '../ui.js';
import { tarefaDe, rotuloImagem } from './comum.js';

export async function render(main, { id }, _consulta, contexto) {
  let sessao = await api.get(`/api/sessoes/${enc(id)}`);
  const corpo = h('div', {});
  let anunciado = false;

  limpar(main, cabecalho('Acompanhar o processamento',
    `Ciclo de testes: ${sessao.ciclo}. Você pode sair desta tela: a execução continua enquanto o programa da interface estiver aberto.`,
    h('a', { href: '#/sessoes' }, '← Sessões')), corpo);

  const imagensPorNome = () => Object.fromEntries(sessao.imagens.map((imagem) => [imagem.nome, imagem]));

  async function agir(corpoPedido, rotulo) {
    try {
      sessao = await api.post(`/api/sessoes/${enc(id)}/falhas`, corpoPedido);
      anunciar(rotulo);
      desenhar();
    } catch (erro) {
      await falhaDaApi(erro);
    }
  }

  function linhaVideo(video) {
    const tarefa = tarefaDe(contexto.estado, { sessao: id, video: video.nome });
    const itens = [h('div', { class: 'linha-entre' }, h('strong', {}, `Extrair os quadros de ${video.nome_original || video.nome}`), estado(video.estado))];

    if (video.estado === 'processando' && tarefa) itens.push(progresso(tarefa.progresso.atual, tarefa.progresso.total, tarefa.progresso.texto));
    if (video.estado === 'concluído') itens.push(h('p', { class: 'pequeno suave' }, `${video.quadros} quadros extraídos; cada quadro é uma imagem da sessão.`));
    if (video.estado === 'falhou') {
      itens.push(mensagem('falha',
        h('p', {}, h('strong', {}, 'Falhou: '), `não foi possível extrair os quadros de ${video.nome_original || video.nome} porque ${video.causa || 'o vídeo não pôde ser lido'}.`),
        h('div', { class: 'linha' },
          h('button', { type: 'button', class: 'botao botao-pequeno', onclick: () => agir({ video: video.nome, acao: 'tentar de novo' }, 'Extração pedida de novo.') }, 'Tentar de novo'),
          h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', onclick: () => agir({ video: video.nome, acao: 'deixar de fora' }, 'Vídeo deixado de fora.') }, 'Deixar de fora'))));
    }
    return h('li', { class: 'cartao' }, itens);
  }

  function linhaExecucao(configuracaoId, execucao) {
    const nome = sessao.configuracoes[configuracaoId]?.nome || configuracaoId;
    const tarefa = tarefaDe(contexto.estado, { sessao: id, configuracao: configuracaoId });
    const itens = [h('div', { class: 'linha-entre' }, h('strong', {}, nome), estado(execucao.estado))];

    if (execucao.estado === 'processando') {
      const atual = tarefa?.progresso.atual ?? execucao.progresso ?? 0;
      const total = tarefa?.progresso.total || execucao.total_atual || 0;
      itens.push(progresso(atual, total, `Processando: ${atual} de ${total} imagens concluídas com a ${nome}.`));
    } else if (execucao.estado === 'na fila') {
      itens.push(h('p', { class: 'pequeno suave' }, 'Aguardando a vez: as configurações rodam uma de cada vez.'));
    } else if (execucao.estado === 'concluído') {
      itens.push(h('p', { class: 'pequeno' }, `${execucao.concluidas.length} imagens segmentadas com a ${nome}.`));
    } else if (execucao.estado === 'falhou') {
      itens.push(mensagem('falha',
        h('p', {}, h('strong', {}, 'Falhou: '), `a execução da ${nome} não terminou porque ${execucao.causa}.`),
        // CE: a solução está fora do sistema; RA: pode tentar de novo aqui
        execucao.sugestao ? h('p', {}, h('strong', {}, execucao.tipo_falha === 'CE' ? 'O que fazer: ' : 'Sugestão: '), execucao.sugestao) : null,
        h('div', { class: 'linha' },
          h('button', { type: 'button', class: 'botao botao-pequeno', onclick: () => agir({ configuracao: configuracaoId, acao: 'tentar de novo' }, 'Execução pedida de novo.') }, 'Tentar de novo'),
          h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', onclick: () => agir({ configuracao: configuracaoId, acao: 'deixar de fora' }, 'Configuração deixada de fora.') }, 'Deixar esta configuração de fora'))));
    }

    // Falha em uma imagem: as outras seguem
    const imagens = imagensPorNome();
    for (const [imagem, falha] of Object.entries(execucao.falhas || {})) {
      itens.push(mensagem('falha',
        h('p', {}, h('strong', {}, 'Falhou: '), `a segmentação da imagem ${rotuloImagem(imagens[imagem] || { nome: imagem })} não terminou porque ${falha.causa}. As outras imagens não foram afetadas.`),
        falha.sugestao ? h('p', {}, h('strong', {}, falha.tipo === 'CE' ? 'O que fazer: ' : 'Sugestão: '), falha.sugestao) : null,
        h('p', {}, 'Você pode tentar de novo ou deixar essa imagem de fora.'),
        h('div', { class: 'linha' },
          h('button', { type: 'button', class: 'botao botao-pequeno', disabled: execucao.estado !== 'concluído',
            onclick: () => agir({ configuracao: configuracaoId, imagem, acao: 'tentar de novo' }, 'Imagem pedida de novo.') }, 'Tentar de novo'),
          h('button', { type: 'button', class: 'botao botao-secundario botao-pequeno', disabled: execucao.estado !== 'concluído',
            onclick: () => agir({ configuracao: configuracaoId, imagem, acao: 'deixar de fora' }, 'Imagem deixada de fora.') }, 'Deixar de fora'))));
    }
    return h('li', { class: 'cartao' }, itens);
  }

  function desenhar() {
    const execucoes = Object.entries(sessao.execucoes);
    const emAndamento = execucoes.some(([, e]) => e.estado === 'na fila' || e.estado === 'processando')
      || sessao.videos.some((v) => v.estado === 'na fila' || v.estado === 'processando');
    const pendentes = execucoes.some(([, e]) => e.estado === 'falhou' || Object.keys(e.falhas || {}).length)
      || sessao.videos.some((v) => v.estado === 'falhou');
    const tratadas = !emAndamento && !pendentes && execucoes.length > 0;

    const total = new Set(execucoes.flatMap(([, e]) => e.concluidas || [])).size;

    limpar(corpo,
      tratadas ? mensagem('ok',
        h('p', {}, h('strong', {}, 'Concluído: '), `as ${total} imagens foram segmentadas. Os resultados estão reunidos nesta `, h('strong', {}, 'sessão'), '.'),
        h('a', { class: 'botao', href: `#/sessao/${enc(id)}/imagem`, id: 'ver-resultado' }, 'Ver os resultados')) : null,
      !execucoes.length ? mensagem('neutra', h('p', {}, 'Nenhuma configuração foi executada nesta sessão.')) : null,
      h('ul', { style: 'list-style:none;padding:0;margin:0', 'aria-live': 'polite' },
        sessao.videos.map(linhaVideo),
        execucoes.map(([configuracaoId, execucao]) => linhaExecucao(configuracaoId, execucao))));

    if (tratadas && !anunciado) {
      anunciado = true;
      anunciar(`Concluído: as ${total} imagens foram segmentadas.`);
      document.getElementById('ver-resultado')?.focus();
    }
  }

  desenhar();

  // Só redesenha quando algo mudou, para não tirar o foco de quem navega pelo teclado
  let ultimo = '';
  return {
    async atualizar(estadoGeral) {
      sessao = await api.get(`/api/sessoes/${enc(id)}`);
      const tarefas = (estadoGeral?.tarefas || []).filter((t) => t.alvo?.sessao === id).map((t) => [t.id, t.estado, t.progresso.atual]);
      const chave = JSON.stringify([sessao.execucoes, sessao.videos, tarefas]);
      if (chave !== ultimo) { ultimo = chave; desenhar(); }
    },
  };
}
