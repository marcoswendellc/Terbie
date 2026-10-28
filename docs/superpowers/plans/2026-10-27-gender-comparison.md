# Comparação de compras por gênero

**Objetivo:** responder comparações entre homens e mulheres com estatística calculada e narrativa determinística.

**Arquitetura:** reconhecer o pedido explícito, preservar shopping/campanha/período e executar uma operação dedicada. Agregar compras únicas por cliente antes da inferência; usar Welch bilateral, IC95% não simultâneo e Holm para três indicadores (gasto total, ticket médio individual e compras por cliente). Exigir ao menos 20 clientes válidos em cada grupo como regra operacional conservadora. Relatar exclusões, diferença absoluta e relativa, p ajustado e limites observacionais. Não inferir causalidade, equivalência nem comportamento de todos os visitantes.

- [x] Escrever testes de ponta a ponta e de referência estatística; verificar falhas.
- [x] Integrar intenção, operação, dependência SciPy e filtros explícitos no compilador.
- [x] Implementar limpeza, agregação por cliente, inferência e apresentação.
- [x] Verificar casos pequenos, dados ausentes/conflitantes, grupos iguais/diferentes e recortes.
- [x] Executar suíte completa, lint e revisão independente.

Validação: 477 testes Python e 11 testes da interface passaram. Dezesseis testes novos cobrem a funcionalidade. Ruff passou nos arquivos alterados; revisão independente concluída. SciPy 1.18.1 instalado no ambiente virtual local e declarado nas dependências. Testes com dados sintéticos; não houve validação da base conectada ou atualização de serviço externo.

Referência do método: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html
