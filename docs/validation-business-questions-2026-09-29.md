# Validação das respostas do Terbie — 29/09/2026

As correções cobrem os exemplos relatados: detalhamento por segmento e gênero,
evolução mensal de notas e faturamento, ranking de campanhas e continuações de conversa.

## Evidência local

- Fonte: `Teste Terbie.xlsx`, aba `Planilha1`, 78.164 registros.
- 27 perguntas na mesma sessão, com combinações em ordem pseudoaleatória (seed 20260929).
- 27/27 passaram após as correções. A comparação verifica dimensões, quantidade de
  linhas, cada indicador calculado e presença dos grupos no texto exibido.
- O resultado esperado é calculado diretamente com pandas, sem reutilizar o compilador
  ou as operações do Terbie.
- Inclui as perguntas fornecidas pelo usuário e as continuações “E por segmento?” e
  “E por gênero?”. Testes sintéticos adicionais incluem dados de outra campanha,
  outro shopping e outro ano, para detectar perda de filtros.
- Resultado detalhado: `evals/business-local-results.json`.

Exemplos conferidos: janeiro de 2026 possui 5.736 compras únicas na planilha local;
a evolução inclui os sete meses com registros disponíveis, sem inventar zeros para
os meses ausentes. O ranking por faturamento retorna Promoção Mães E Namorados 2026,
Buriti Shopping, com R$ 6.156.490,84.

## Causas corrigidas

1. Anotações como `(nm_segmento)` eram confundidas com valores de filtro.
2. Consultas de indicadores descartavam o agrupamento antes da agregação ou seleção.
3. Dimensões contendo valores numéricos eram classificadas como indicadores pelo narrador;
   o texto acabava mostrando somente a primeira linha, mesmo com dados corretos.
4. A evolução mensal não tinha uma operação para derivar o mês da data da compra.
5. O diretor podia reescrever um pedido explícito e perder mês, dimensão ou recorte.
6. Continuações precisavam preservar filtros executados e indicadores, sem herdar a
   dimensão anterior quando o usuário solicita outra.

O gráfico usa exclusivamente os pontos calculados. Séries com dimensões adicionais
são apresentadas em tabela, sem juntar segmentos diferentes em uma linha única.
Campanhas em um ano usam sobreposição da vigência; evolução mensal usa a data da compra.

## Reproduzir

```powershell
.\venv\Scripts\python.exe -m scripts.evaluate_business_questions
.\venv\Scripts\python.exe -c "from app.core.config import Settings; Settings.model_config['env_file']=None; import pytest; raise SystemExit(pytest.main(['-q']))"
node --test tests/test_chat_conversation.cjs
```

## Limites da validação

Os testes são evidência dos casos cobertos, não uma garantia para qualquer pergunta.
Não foi validada a planilha online do Google Sheets nem o comportamento real do Gemini.
A tentativa com os provedores configurados encontrou `ConnectError` e utilizou o
fallback local. O arquivo `evals/business-live-results.json` identifica essa limitação;
seus resultados não representam validação externa.

A execução com rede foi rejeitada pela revisão automática de aprovação por exigir
autorização explícita para enviar schema e resultados agregados empresariais ao Gemini.
O comando `--live` permanece preparado para execução após essa autorização e registra
se houve respostas reais do provedor, para não confundir fallback com teste online.
