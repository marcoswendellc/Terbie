const {spawn} = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const root = path.resolve('app/web');
  const server = http.createServer((req, res) => {
    const asset = req.url === '/' ? 'index.html' : req.url.replace(/^\/ui\//, '');
    const file = path.resolve(root, asset);
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) {
      res.writeHead(404).end(); return;
    }
    res.setHeader('Content-Type', ({'.html':'text/html', '.css':'text/css', '.js':'text/javascript', '.png':'image/png'})[path.extname(file)] || 'application/octet-stream');
    res.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'terbie-responsive-'));
  const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
    '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', '--disable-background-networking', 'about:blank',
  ], {windowsHide:true});
  let socket;
  try {
    const endpoint = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Chrome startup timed out')), 15000);
      chrome.on('error', reject);
      chrome.stderr.on('data', chunk => {
        const match = String(chunk).match(/DevTools listening on (ws:\/\/[^\s]+)/);
        if (match) {clearTimeout(timer); resolve(match[1]);}
      });
    });
    const port = new URL(endpoint).port;
    const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
    socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl);
    await new Promise(resolve => socket.addEventListener('open', resolve, {once:true}));
    const pending = new Map();
    let id = 0;
    socket.addEventListener('message', ({data}) => {
      const message = JSON.parse(data);
      if (pending.has(message.id)) {
        const {resolve, reject} = pending.get(message.id);
        pending.delete(message.id);
        message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result);
      }
    });
    const command = (method, params = {}) => new Promise((resolve, reject) => {
      pending.set(++id, {resolve, reject});
      socket.send(JSON.stringify({id, method, params}));
    });
    const evaluate = async expression => {
      const result = await command('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true});
      if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    };
    await command('Page.enable');
    await command('Page.navigate', {url:`http://127.0.0.1:${server.address().port}/`});
    for (let i = 0; i < 100; i++) {
      if (await evaluate("document.readyState === 'complete' && typeof appendMessage === 'function'")) break;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    for (const [width, height] of [[320,640],[390,844],[768,1024],[1024,768],[1440,900],[844,390],[390,380]]) {
      await command('Emulation.setDeviceMetricsOverride', {width,height,deviceScaleFactor:1,mobile:width<1024});
      await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
      const login = await evaluate("showLogin(); ({width:innerWidth, scroll:document.documentElement.scrollWidth})");
      assert.ok(login.scroll <= width, `Login overflow ${width}: ${JSON.stringify(login)}`);
      const metrics = await evaluate(`(() => {
        showChat();
        messages.replaceChildren();
        appendMessage('user', 'Quais segmentos são mais consumidos por cada faixa etária?');
        appendMessage('app', '| Faixa etária | Segmento | Faturamento | Compras | Clientes únicos | Ticket por compra |\\n|---|---|---:|---:|---:|---:|\\n| 25-34 | Calçados & Acessórios >> Calçados Geral | R$ 2.025.302,16 | 6.695 | 4.512 | R$ 302,51 |');
        const rect = selector => {const r=document.querySelector(selector).getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width};};
        return {width:innerWidth,scroll:document.documentElement.scrollWidth, composer:rect('.composer'), send:rect('.send-button'), table:rect('.table-scroll'), shell:rect('.conversation-shell')};
      })()`);
      assert.ok(metrics.scroll <= width, `Chat overflow ${width}: ${JSON.stringify(metrics)}`);
      assert.ok(metrics.send.right <= width && metrics.send.bottom <= height, `Composer clipped: ${JSON.stringify(metrics)}`);
      assert.ok(metrics.table.right <= width, `Table overflow: ${JSON.stringify(metrics)}`);
      if (width < 1024) {
        const menu = await evaluate(`(() => {document.querySelector('[data-menu]').click(); const r=document.querySelector('.conversation-shell').getBoundingClientRect(); return {width:r.width,inert:document.querySelector('.conversation-shell').inert,open:chatView.classList.contains('menu-open')};})()`);
        assert.equal(menu.width, metrics.shell.width);
        assert.equal(menu.open, true);
        assert.equal(menu.inert, true);
        await evaluate("document.querySelector('[data-menu-backdrop]').click()");
      }
      console.log(`PASS ${width}x${height}: login, chat, table, composer${width<1024?', overlay menu':''}`);
    }
  } finally {
    socket?.close();
    chrome.kill();
    server.close();
  }
})().catch(error => {console.error(error); process.exitCode=1;});
