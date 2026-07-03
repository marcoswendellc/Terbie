# Terbie

Terral BI Copilot Engine.

## Arquitetura

O Terbie e um motor analitico conversacional orientado por contratos. Ele separa
interpretacao semantica, conhecimento de negocio, compilacao analitica,
planejamento e futura execucao.

Documentos principais:

- [Visao geral da arquitetura](docs/architecture/overview.md)
- [Planner Specification v1](docs/planner-specification-v1.md)
- [Architecture Decision Records](docs/adr/)

## Dependencias

O provider Gemini usa o pacote `google-genai`.

```powershell
pip install google-genai
```

## Releases

- [v0.1.0 — Foundation](docs/releases/v0.1.0.md)
