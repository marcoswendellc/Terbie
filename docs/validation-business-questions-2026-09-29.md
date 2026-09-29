# Validação das respostas do Terbie — 29/09/2026

As correções cobrem os exemplos relatados: detalhamento por segmento e gênero,
evolução mensal de notas e faturamento, ranking de campanhas e continuações de conversa.

## Evidência local

- Fonte: `Teste Terbie.xlsx`, aba `Planilha1`, 78.164 registros.
- 35 perguntas na mesma sessão, com combinações em ordem pseudoaleatória (seed 20260929).
- 35/35 passaram após as correções. A comparação verifica dimensões, quantidade de
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
Não foi validada a planilha online do Google Sheets. Após autorização explícita do usuário,
a execução com rede foi realizada usando o Gemini configurado e a planilha local.
A bateria principal passou 27/27 casos, com 5 respostas reais do provedor em 27 tentativas.
A bateria adicional de geografia/perfil passou 8/8 casos, com 1 resposta real do provedor
em 8 tentativas; ocorreram 6 `ClientError` e 1 `ServerError` nas demais chamadas.
As respostas do provedor incluem sugestões de aprofundamento. Os cálculos dos pedidos
explícitos usam o motor determinístico; esses números não significam que o modelo
interpretou ou narrou todas as perguntas com sucesso. O fallback permanece necessário.
Relatórios: `evals/business-live-results.json` e `evals/business-live-results-27.json`.

## Geografia e perfil de compras

- Cidade usa `localidade` quando a fonte não possui uma coluna `cidade`.
- UF e cidade são filtros distintos; o ticket usa somente as compras selecionadas.
- “Bairro apresentou maior volume” mantém bairro como dimensão e exclui nomes ausentes.
- `maio/26` corresponde a 01–31/05/2026 na data da compra.
- O perfil informa clientes únicos, compras, ticket, compras por cliente, grupos predominantes
  e ausência de dados. Percentuais de predominância usam os clientes com informação preenchida.
- A idade é calculada na data da análise; datas ISO de nascimento preservam mês e dia.
- A continuação “e do GO?” mantém o período e o denominador do ticket anterior.

Na planilha local, maio contém 17.966 clientes e 32.802 compras, ticket de R$ 345,04.
O ranking de bairro de 2026 retorna Parque Amazônia, com 3.257 notas.
Tickets sem filtro de período: Goiânia R$ 312,30; Aparecida de Goiânia R$ 317,56;
GO R$ 332,72; SP R$ 303,87.
