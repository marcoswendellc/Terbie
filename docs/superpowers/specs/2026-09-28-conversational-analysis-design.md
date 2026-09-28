# Investigação analítica conversacional

## Objetivo aprovado
Gestores exploram campanhas, público e desempenho em linguagem natural. O Terbie
escolhe análises necessárias à pergunta, explica suas escolhas e oferece até dois
aprofundamentos. O usuário pode escolher uma sugestão ou mudar o rumo livremente.

## Integração
O endpoint `/execute` continua sendo a entrada. Uma direção conversacional opcional,
ativada com o provider Gemini, recebe pergunta, histórico da sessão, catálogo e
nomes/tipos de colunas. Retorna objetivo, premissas e até três perguntas analíticas
autossuficientes, ou um esclarecimento. Cada pergunta passa pelo compilador,
validador, executor e verificador existentes. Não há execução de código da LLM.

Uma segunda decisão, depois dos resultados, propõe até duas sugestões com rótulo,
pergunta completa e colunas necessárias. Sugestões incompatíveis com o schema são
descartadas. Uma compilação determinística local confere também as dependências
do plano e das dimensões reconhecidas, sem executar dados nem chamar outra LLM.
Sugestões que esse preflight não consegue validar são omitidas; texto livre continua
usando a interpretação por LLM. São armazenadas na sessão e exibidas como ações; texto livre
continua disponível. Escolher uma sugestão executa sua pergunta no próximo turno.

## Contexto e limites
O histórico registra a pergunta original, as perguntas efetivamente analisadas,
objetivo, resultados governados e sugestões. O diretor deve produzir recortes
completos, substituindo filtros quando o usuário redireciona a conversa. Consultas
internas não são novos turnos e não herdam filtros novamente.

Máximo de três análises por turno; prazo cooperativo de 60 segundos para iniciar
novas etapas. Chamadas Gemini têm timeout próprio limitado ao tempo restante;
operações pandas já iniciadas não são interrompidas. Não há pesquisas adicionais
automáticas após responder. Falhas parciais são apresentadas explicitamente.

## Governança e respostas
Dados brutos e credenciais não entram nos prompts. O narrador e o gerador de
sugestões recebem somente saídas sanitizadas; resultados que falham na verificação
não podem sustentar conclusões. As regras de governança precedem a narrativa tanto
na consulta simples como na composta. A documentação deve refletir que agregados
governados podem ser enviados à LLM, em contraste com a proibição antiga de todo
resultado. Compras registradas não são apresentadas como fluxo total de visitantes.

Falha do diretor mantém o caminho analítico existente com aviso. Sem Gemini, esse
caminho continua disponível. Novos campos da resposta têm defaults compatíveis.

## Validação
Testes com dados sintéticos e provider controlado cobrem escolha de análises,
resultados numéricos, seleção por rótulo/ordinal, redirecionamento, isolamento entre
sessões, ausência de colunas, falhas, limites e sanitização anterior à narrativa.
Testes do provider usam cliente simulado, sem credenciais nem chamadas externas.
Suite Python completa e verificação JavaScript completam a validação local.

## Execução
O usuário autorizou a execução após aprovar o comportamento. Trabalho no checkout
aberto, preservando as alterações locais existentes; sem publicação ou merge.
