// Chamadas ao servidor local. As recusas (PA, AL, RA, CE) chegam como ErroApi com a fala já pronta.

export class ErroApi extends Error {
  constructor(erro, status) {
    super(erro?.mensagem || 'Não foi possível concluir a ação.');
    this.tipo = erro?.tipo || 'CE';
    this.campo = erro?.campo || null;
    this.dados = erro?.dados || {};
    this.status = status;
  }
}

async function pedir(metodo, url, corpo, { formulario = false } = {}) {
  const opcoes = { method: metodo, headers: {} };

  if (formulario) {
    opcoes.body = corpo;
  } else if (corpo !== undefined) {
    opcoes.headers['Content-Type'] = 'application/json';
    opcoes.body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(url, opcoes);
  } catch {
    throw new ErroApi({
      tipo: 'CE',
      mensagem: 'Não foi possível falar com o sistema. Confira se o programa da interface continua aberto no computador.',
    }, 0);
  }

  const texto = await resposta.text();
  let dados = null;
  try { dados = texto ? JSON.parse(texto) : null; } catch { dados = null; }

  if (!resposta.ok) {
    throw new ErroApi(dados?.erro || { tipo: 'CE', mensagem: 'O sistema não conseguiu concluir a ação.' }, resposta.status);
  }
  return dados;
}

// Envio de arquivos com progresso (fetch não informa quanto já foi enviado)
function enviarComProgresso(url, formData, aoProgredir) {
  return new Promise((resolver, rejeitar) => {
    const pedido = new XMLHttpRequest();
    pedido.open('POST', url);
    pedido.upload.onprogress = (evento) => {
      if (evento.lengthComputable && aoProgredir) aoProgredir(evento.loaded, evento.total);
    };
    pedido.onerror = () => rejeitar(new ErroApi({
      tipo: 'CE', mensagem: 'Não foi possível falar com o sistema. Confira se o programa da interface continua aberto no computador.',
    }, 0));
    pedido.onload = () => {
      let dados = null;
      try { dados = pedido.responseText ? JSON.parse(pedido.responseText) : null; } catch { dados = null; }
      if (pedido.status >= 200 && pedido.status < 300) resolver(dados);
      else rejeitar(new ErroApi(dados?.erro || { tipo: 'CE', mensagem: 'O sistema não conseguiu concluir a ação.' }, pedido.status));
    };
    pedido.send(formData);
  });
}

export const api = {
  get: (url) => pedir('GET', url),
  post: (url, corpo = {}) => pedir('POST', url, corpo),
  put: (url, corpo = {}) => pedir('PUT', url, corpo),
  delete: (url) => pedir('DELETE', url),
  enviar: (url, formData, aoProgredir) => enviarComProgresso(url, formData, aoProgredir),
};

export const enc = encodeURIComponent;
