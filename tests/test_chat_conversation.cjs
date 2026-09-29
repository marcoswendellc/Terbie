const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');

function harness() {
  class Element {
    constructor() {
      this.children = [];
      this.dataset = {};
      this.listeners = {};
      this.style = {};
      this.classList = {add() {}, remove() {}};
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
    document, sessionStorage: {getItem() { return null; }, setItem() {}},
    crypto: {randomUUID: () => 'session'}, console,
  });
  vm.runInContext(fs.readFileSync('app/web/app.js', 'utf8'), context);
  return {context, nodes, Element};
}

test('response displays analytical assumptions without technical metadata', () => {
  const {context} = harness();
  const answer = context.formatExecuteResponse({
    answer: 'Vendas registradas: R$ 300.',
    assumptions: ['Campanhas de 2026.'], metadata: {internal: 'secret'},
  });
  assert.match(answer, /Campanhas de 2026/);
  assert.doesNotMatch(answer, /secret/);
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
