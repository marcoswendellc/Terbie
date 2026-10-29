const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');

function harness({mobile = false} = {}) {
  class Element {
    constructor() {
      this.children = [];
      this.dataset = {};
      this.listeners = {};
      this.style = {};
      const classes = new Set();
      this.classList = {
        add(...names) { names.forEach(name => classes.add(name)); },
        remove(...names) { names.forEach(name => classes.delete(name)); },
        contains(name) { return classes.has(name); },
        toggle(name) {
          if (classes.has(name)) { classes.delete(name); return false; }
          classes.add(name); return true;
        },
      };
    }
    append(...children) { this.children.push(...children); }
    appendChild(child) { this.children.push(child); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(type, handler) { this.listeners[type] = handler; }
    focus() {}
    setAttribute(name, value) { this[name] = value; }
    querySelector() { return this; }
    querySelectorAll() { return []; }
    requestSubmit() { this.submitted = true; }
  }
  const nodes = new Map();
  const document = {
    createElement: () => new Element(),
    createElementNS: () => new Element(),
    querySelector: selector => {
      if (!nodes.has(selector)) nodes.set(selector, new Element());
      return nodes.get(selector);
    },
    querySelectorAll: () => [],
  };
  const context = vm.createContext({
    window: {matchMedia: () => ({matches: mobile, addEventListener() {}})},
    document, sessionStorage: {getItem() { return null; }, setItem() {}},
    crypto: {randomUUID: () => 'session'}, console,
  });
  vm.runInContext(fs.readFileSync('app/web/app.js', 'utf8'), context);
  return {context, nodes, Element};
}

test('desktop sidebar collapses and reopens without resetting conversation', () => {
  const {context, nodes} = harness();
  const chat = nodes.get('[data-view="chat"]');
  const menu = nodes.get('[data-menu]');
  assert.equal(menu['aria-expanded'], 'true');
  menu.listeners.click();
  assert.equal(chat.classList.contains('sidebar-collapsed'), true);
  assert.equal(menu['aria-expanded'], 'false');
  context.closeMenu();
  assert.equal(chat.classList.contains('sidebar-collapsed'), true);
  menu.listeners.click();
  assert.equal(chat.classList.contains('sidebar-collapsed'), false);
  assert.equal(menu['aria-expanded'], 'true');
});

test('mobile sidebar opens and closes with Escape', () => {
  const {nodes} = harness({mobile: true});
  const chat = nodes.get('[data-view="chat"]');
  const menu = nodes.get('[data-menu]');
  assert.equal(menu['aria-expanded'], 'false');
  menu.listeners.click();
  assert.equal(chat.classList.contains('menu-open'), true);
  assert.equal(menu['aria-expanded'], 'true');
  chat.listeners.keydown({key: 'Escape'});
  assert.equal(chat.classList.contains('menu-open'), false);
  assert.equal(menu['aria-expanded'], 'false');
});

test('mobile menu closes using its close button or backdrop', () => {
  const {nodes} = harness({mobile: true});
  const chat = nodes.get('[data-view="chat"]');
  const menu = nodes.get('[data-menu]');
  menu.listeners.click();
  nodes.get('[data-close-menu]').listeners.click();
  assert.equal(chat.classList.contains('menu-open'), false);
  menu.listeners.click();
  nodes.get('[data-menu-backdrop]').listeners.click();
  assert.equal(chat.classList.contains('menu-open'), false);
  assert.equal(menu['aria-expanded'], 'false');
});

test('response displays analytical assumptions without technical metadata', () => {
  const {context} = harness();
  const answer = context.formatExecuteResponse({
    answer: 'Vendas registradas: R$ 300.',
    assumptions: ['Campanhas de 2026.'], metadata: {internal: 'secret'},
  });
  assert.match(answer, /Campanhas de 2026/);
  assert.doesNotMatch(answer, /secret/);
});

test('password visibility can be toggled and announces its state', () => {
  const {nodes} = harness();
  // The input is queried lazily by the event handler.
  const button = nodes.get('[data-toggle-password]');
  button.listeners.click();
  const password = nodes.get('#login-password');
  password.type = 'password';
  button.listeners.click();
  assert.equal(password.type, 'text');
  assert.equal(button['aria-pressed'], 'true');
  button.listeners.click();
  assert.equal(password.type, 'password');
  assert.equal(button['aria-pressed'], 'false');
});

test('remembered sessions restore valid tokens and discard expired tokens', () => {
  const {context} = harness();
  let value = JSON.stringify({token: 'signed-token', expiresAt: Date.now() + 60000});
  context.localStorage = {getItem: () => value, removeItem: () => { value = null; }};
  assert.equal(context.rememberedSession().token, 'signed-token');
  value = JSON.stringify({token: 'expired-token', expiresAt: Date.now() - 1});
  assert.equal(context.rememberedSession(), null);
  assert.equal(value, null);
});

test('suggestion buttons submit the full scoped question and use safe text', () => {
  const {context, nodes, Element} = harness();
  const message = new Element();
  context.appendFollowUpSuggestions(message, {suggestions: [
    {label: '<b>Perfil</b>', question: 'Perfil dos clientes da campanha Mães 2026 no Sul'},
  ]});
  const block = message.children[0];
  const button = block.children.find(child => child.textContent === '<b>Perfil</b>');
  assert.ok(button);
  button.listeners.click();
  assert.equal(nodes.get('[data-message-input]').value, 'Perfil dos clientes da campanha Mães 2026 no Sul');
  assert.equal(nodes.get('[data-chat-form]').submitted, true);
});

test('no placeholder suggestions when none were returned', () => {
  const {context, Element} = harness();
  const message = new Element();
  context.appendFollowUpSuggestions(message, {suggestions: []});
  assert.equal(message.children.length, 0);
});

test('monthly chart renders every computed point and an accessible label', () => {
  const {context, Element} = harness();
  const message = new Element();
  context.appendAnalysisChart(message, {
    metadata: {chart: {type: 'line', x: 'mes', y: 'faturamento', title: 'Faturamento'}},
    data: [{mes: '2026-01', faturamento: 10}, {mes: '2026-02', faturamento: 30},
      {mes: '2026-08', faturamento: 20}],
  });
  const svg = message.children[0];
  assert.equal(svg.role, 'img');
  assert.match(svg['aria-label'], /Faturamento/);
  assert.equal(svg.children.filter(child => child.r === '4').length, 3);
  assert.equal(svg.children.filter(child => child.textContent?.startsWith('2026-')).length, 3);
});

test('monthly chart ignores invalid or missing analytical data', () => {
  const {context, Element} = harness();
  const message = new Element();
  context.appendAnalysisChart(message, {metadata: {}, data: []});
  context.appendAnalysisChart(message, {metadata: {chart: {x: 'mes', y: 'faturamento'}},
    data: [{mes: '2026-01', faturamento: 'invalid'}]});
  assert.equal(message.children.length, 0);
});

test('fallback keeps the originating chat session', async () => {
  const {context} = harness();
  const bodies = [];
  context.fetch = async (_endpoint, options) => {
    bodies.push(JSON.parse(options.body));
    if (bodies.length === 1) return {ok: false, json: async () => ({detail: 'unavailable'})};
    return {ok: true, json: async () => ({response: 'Tente novamente.'})};
  };
  await context.askBackend('Campanhas?', 'original-chat');
  assert.equal(bodies.length, 2);
  assert.equal(bodies[0].session_id, 'original-chat');
  assert.equal(bodies[1].session_id, 'original-chat');
});

test('campaign listing keeps four separate headers and shopping and dates in each row', () => {
  const {context, Element} = harness();
  const content = new Element();
  context.renderMessageContent(content, [
    'Em 2026 ocorreram duas campanhas:', '',
    '| Campanha | Shopping | Início | Fim |', '|---|---|---:|---:|',
    '| Promoção Pais 2026 | Buriti Shopping | 22/07/2026 | 23/08/2026 |',
    '| Promoção Pais 2026 | Shopping Sul | 04/08/2026 | 11/08/2026 |',
    '', 'Inclui campanhas com vigência em 2026.',
  ].join('\n'), 'assistant');
  const table = content.children.find(child => child.className === 'table-scroll').children[0];
  assert.deepEqual(Array.from(table.children[0].children[0].children, cell => cell.textContent),
    ['Campanha', 'Shopping', 'Início', 'Fim']);
  const rows = table.children[1].children;
  assert.equal(rows.length, 2);
  assert.equal(rows[0].children.length, 4);
  assert.equal(rows[0].children[1].textContent, 'Buriti Shopping');
  assert.equal(rows[1].children[1].textContent, 'Shopping Sul');
  assert.equal(rows[1].children[3].textContent, '11/08/2026');
});

test('collapsed markdown tables render as rows instead of pipe text', () => {
  const {context, Element} = harness();
  const content = new Element();
  context.renderMessageContent(content,
    '| Loja | Faturamento ||---|---:|| SUPERMERCADO TATICO | R$ 362.155,21 || FLAVIOS | R$ 228.710,56 |',
    'assistant');
  const wrapper = content.children.find(child => child.className === 'table-scroll');
  assert.ok(wrapper);
  const table = wrapper.children[0];
  assert.equal(table.children[1].children.length, 2);
  assert.equal(table.children[1].children[0].children[0].textContent, 'SUPERMERCADO TATICO');
  assert.equal(table.children[1].children[0].children[1].className, 'numeric-cell');
  assert.equal(wrapper.tabIndex, 0);
});

test('analysis scope is separate and collapsible while answer remains visible', () => {
  const {context, Element} = harness();
  const content = new Element();
  context.renderMessageContent(content,
    'A loja líder foi Tatico.\n\nRecorte considerado: Campanha de mães de 2026 no Portal Shopping.',
    'assistant');
  assert.equal(content.children[0].textContent, 'A loja líder foi Tatico.');
  const scope = content.children.find(child => child.className === 'analysis-scope');
  assert.ok(scope);
  assert.equal(scope.children[0].textContent, 'Recorte da análise');
  assert.match(scope.children[1].textContent, /Portal Shopping/);
  assert.equal(scope.open, undefined);
});

test('table cell content is rendered as text and user messages are not interpreted', () => {
  const {context, Element} = harness();
  const content = new Element();
  context.renderMessageContent(content,
    '| Loja | Compras |\n|---|---:|\n| <img src=x onerror=alert(1)> | 2 |', 'assistant');
  const table = content.children[0].children[0];
  assert.equal(table.children[1].children[0].children[0].textContent,
    '<img src=x onerror=alert(1)>');
  context.renderMessageContent(content, '| Loja | Compras ||---|---|| A | 2 |', 'user');
  assert.equal(content.children.length, 0);
  assert.match(content.textContent, /\| Loja/);
});
