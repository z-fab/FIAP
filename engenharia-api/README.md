# Do Notebook à Produção — Engenharia de Software para Data Science & APIs

Material de aula para o curso de **Machine Learning Engineering** (PosTech FIAP) sobre como levar um modelo de ML de uma célula de notebook até um pacote testado, servido por uma API e pronto para produção.

O fio condutor é o dataset **California Housing**: refatoração de código, pipeline reprodutível, testes, API FastAPI e tooling profissional.

## O que você vai aprender

- **Refatoração & Pipeline** — transformar notebook em módulos `src/` com SOLID e encapsular pré-processamento num Pipeline reprodutível
- **Testes em ML** — pirâmide de testes com pytest, validação de schema (pandera) e smoke tests
- **API de inferência** — expor o modelo com FastAPI, Pydantic, `/predict`, `/health` e padrões de serving
- **Empacotamento & Tooling** — uv, ruff, taskipy, Makefile e versionamento conjunto de modelo + API

## Conteúdo

### Textbook interativo (`text-book/`)

Textbook em HTML/CSS/JS com 4 capítulos navegáveis, lidos direto no navegador:

| Capítulo | Tema | Interativos |
|----------|------|-------------|
| **01** · Refatoração & Pipeline | Notebook vs. produção, SOLID em ML, anatomia de repositório, módulos `src/` e Pipeline sklearn | Diagrama de repositório · Mapa da refatoração · Fluxo do Pipeline · Tabs antes/depois |
| **02** · Testes em ML | Pirâmide de testes, pytest, validação de schema (pandera) e smoke tests | Diagrama da pirâmide · Anatomia Arrange→Act→Assert · Portão de dados |
| **03** · API com FastAPI | REST, Pydantic, endpoints `/predict` e `/health`, observabilidade e padrões de serving | Accordion de status HTTP · Ciclo de request · Middleware e latência · Animação batch vs online |
| **04** · Empacotamento & Tooling | uv, `pyproject.toml`, ruff, taskipy, Makefile, versionamento modelo+API e README do projeto | Fluxo uv→pacote · Decisão de versionamento · Construir vs serving pronto |

**Stack visual:** HTML + Tailwind CDN + Alpine.js + Prism.js · tudo estático, sem build step · ~55 min de leitura.

### Código prático (`codigos/`)

Implementação hands-on do California Housing que acompanha os capítulos — refatoração, testes, API e empacotamento. *(Em breve.)*

**Pré-requisitos (quando disponível):** Python 3.11+ e [uv](https://docs.astral.sh/uv/getting-started/installation/).

## Quickstart

### Opção 1 — Makefile

```bash
make textbook    # sobe o textbook e abre no navegador (Ctrl+C para parar)
make help        # lista todos os alvos
```

Por padrão, sobe em [http://localhost:8000](http://localhost:8000).

### Opção 2 — Python direto

```bash
cd text-book && python3 -m http.server 8000
```

Depois abra [http://localhost:8000/index.html](http://localhost:8000/index.html).

## Estrutura do Repositório

```
engenharia-api/
├── text-book/
│   ├── index.html                 # homepage com cards dos 4 capítulos
│   ├── assets/
│   │   ├── style.css              # design system (DM Sans + DM Serif + paleta)
│   │   └── main.js                # helpers: sidebar, progresso, scroll-spy
│   └── capitulos/
│       ├── 01-refatoracao-pipeline.html
│       ├── 02-testes.html
│       ├── 03-api-fastapi.html
│       └── 04-empacotamento-tooling.html
├── codigos/                       # implementação prática (em breve)
├── Makefile                       # atalhos para servir o textbook
└── README.md                      # este arquivo
```

## Comandos Disponíveis

```bash
make help       # lista todos os alvos
make textbook   # serve o textbook e abre no navegador
```

Variável configurável: `PORT` (padrão `8000`).

Exemplo: `make textbook PORT=3000`

## Persistência Local

Alguns interativos salvam estado no `localStorage` do navegador:

- Progresso de leitura (`visited_{capitulo}.html`) — visível na sidebar e no index.
- Estado da sidebar recolhida (`tb_sidebar_collapsed`).

Para resetar, limpe os dados do site no navegador ou use as ferramentas de desenvolvedor.

## Stack e dependências

### Textbook (via CDN — nenhum build step)

| Camada | Biblioteca |
|--------|------------|
| Layout | Tailwind CSS |
| Reatividade | Alpine.js |
| Tipografia | DM Serif Display + DM Sans + JetBrains Mono (Google Fonts) |
| Syntax highlight | Prism.js |

### Código prático (quando disponível)

| Ferramenta | Uso |
|------------|-----|
| uv | Gerenciamento de ambiente e dependências |
| scikit-learn | Pipeline e modelo (California Housing) |
| pytest | Testes automatizados |
| pandera | Validação de schema |
| FastAPI + Pydantic | API de inferência |
| ruff | Lint e format |
| taskipy | Atalhos de tarefas (`train`, `test`, `run`) |
