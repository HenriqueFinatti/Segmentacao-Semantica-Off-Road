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

export const api = {
  get: (url) => pedir('GET', url),
  post: (url, corpo = {}) => pedir('POST', url, corpo),
  put: (url, corpo = {}) => pedir('PUT', url, corpo),
  delete: (url) => pedir('DELETE', url),
  enviar: (url, formData) => pedir('POST', url, formData, { formulario: true }),
};

export const enc = encodeURIComponent;
