# Notebooks Complementares

Material opcional para aprofundamento nos temas do curso. Cada notebook aborda um conceito de forma isolada e prática, sem depender dos outros. Use quando quiser entender melhor o funcionamento interno de alguma tecnologia antes ou depois de assistir à aula correspondente.

## Pre-requisitos

- Python 3.11 ou superior
- [`uv`](https://docs.astral.sh/uv/) instalado globalmente
- Variavel de ambiente `GEMINI_API_KEY` configurada

```bash
export GEMINI_API_KEY="sua-chave-aqui"
```

## Como rodar

```bash
cd notebooks && uv run jupyter notebook
```

O ambiente virtual e as dependencias sao criados automaticamente pelo `uv` com base no `pyproject.toml` deste diretorio.

## Notebooks disponiveis

| Arquivo | Tema | Quando usar |
|---|---|---|
| `01-gemini-api-basics.ipynb` | Fundamentos da API do Gemini — geração de texto, streaming, tool calling | Antes do Stage 01, para entender o que o `agent.py` usa por baixo |
| `02-sse-under-the-hood.ipynb` | SSE em nivel de protocolo — formato do wire, producer, consumer, comparação com WebSocket | Antes do Stage 02, para entender o que o FastAPI abstrai |
| `03-langgraph-internals.ipynb` | Grafo ReAct do LangGraph — nodes, edges, estado, ciclo de execução | Antes do Stage 01, para entender como o agente decide chamar ferramentas |
| `04-celery-task-lifecycle.ipynb` | Ciclo de vida de tarefas Celery — estados, retry, resultado, monitoramento | Antes do Stage 03, para entender a fila de tarefas assincrona |
| `05-docker-compose-networking.ipynb` | Redes no Docker Compose — DNS interno, healthcheck, depends_on, portas | Qualquer momento em que o compose parecer magico |

## Observacao

Os notebooks sao independentes entre si. Nao ha uma ordem obrigatoria de execucao. Cada um instala suas proprias dependencias na primeira celula de codigo.
