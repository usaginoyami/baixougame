const REPO = 'usaginoyami/baixougame';
const WORKFLOW = 'add-game.yml';
const MAX = 150;
const KEY = 'baixougame-token';
const $ = id => document.getElementById(id);

function store(op, value) {
  try {
    if (op === 'get') return localStorage.getItem(KEY) || '';
    if (op === 'set') localStorage.setItem(KEY, value);
    if (op === 'del') localStorage.removeItem(KEY);
  } catch (err) { /* sem armazenamento: o token vale só para esta aba */ }
  return '';
}
let token = store('get');

function parseNames() {
  const seen = new Set(), out = [];
  for (const raw of $('names').value.split(/[\r\n;]+/)) {
    const name = raw.replace(/\s+/g, ' ').trim();
    const key = name.toLowerCase();
    if (name && !seen.has(key)) { seen.add(key); out.push(name); }
  }
  return out;
}

function say(text, kind, link) {
  const el = $('status');
  el.className = 'status' + (kind ? ' ' + kind : '');
  el.replaceChildren(text);
  if (link) {
    el.append(' ');
    const a = document.createElement('a');
    a.href = link; a.target = '_blank'; a.rel = 'noopener'; a.textContent = 'Abrir execução no GitHub';
    el.append(a);
  }
}

function refresh() {
  const names = parseNames();
  $('count').textContent = `${names.length} ${names.length === 1 ? 'jogo' : 'jogos'}`;
  $('count').classList.toggle('over', names.length > MAX);
  $('send').disabled = !token || !names.length || names.length > MAX;
  $('token-saved').hidden = !token;
  $('token-form').hidden = !!token;
}

async function send() {
  const names = parseNames();
  if (!token || !names.length || names.length > MAX) return;
  $('send').disabled = true;
  say('Enviando…');
  try {
    const res = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method: 'POST',
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${token}`,
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ref: 'main', inputs: { nome: names.join('; ') } }),
    });
    if (res.status === 204) {
      say(`Pronto: ${names.length} ${names.length === 1 ? 'nome enviado' : 'nomes enviados'}. O cadastro roda no GitHub e os jogos aparecem no site em alguns minutos.`, 'good',
        `https://github.com/${REPO}/actions/workflows/${WORKFLOW}`);
      $('names').value = '';
    } else if (res.status === 401) {
      say('O GitHub recusou o token (inválido ou vencido). Esqueça o token e cole um novo.', 'bad');
    } else if (res.status === 403 || res.status === 404) {
      say('O token não tem permissão neste repositório. Confira se ele é do repositório baixougame e tem Actions: Read and write.', 'bad');
    } else if (res.status === 422) {
      say('O GitHub recusou a lista (talvez grande demais). Envie menos jogos por vez.', 'bad');
    } else {
      say(`O GitHub respondeu com erro ${res.status}. Nada foi enviado, tente de novo.`, 'bad');
    }
  } catch (err) {
    say('Não consegui falar com o GitHub. Confira a conexão e tente de novo. Nada foi enviado.', 'bad');
  }
  refresh();
}

$('max').textContent = MAX;
$('names').addEventListener('input', refresh);
$('send').addEventListener('click', send);
$('save').addEventListener('click', () => {
  const t = $('token').value.trim();
  if (!t) return;
  token = t; store('set', t); $('token').value = ''; say(''); refresh();
});
$('forget').addEventListener('click', () => { token = ''; store('del'); refresh(); });
refresh();
