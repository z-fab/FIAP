# Documentação em ML — do Model Card ao Tech Challenge

Material de aula para o curso de **Machine Learning Engineering** (PosTech FIAP) sobre como documentar projetos de ML com rigor, do código aos artefatos de governança.

## Conteúdo

### Textbook interativo (`textbook/`)

Textbook em HTML/CSS/JS com 6 capítulos navegáveis, lidos direto no navegador:

| Capítulo | Tema | Interativos |
|----------|------|-------------|
| **01** · Por que documentação importa | Custo invisível de não documentar — casos Zillow, COMPAS, Amazon Hiring | Timeline de incidentes · Quiz de diagnóstico |
| **02** · Model Cards | As 9 seções canônicas de Mitchell et al. (2019) + evolução para System Cards | Explorador das 9 seções · Comparador bom vs ruim |
| **03** · README + Mermaid | Anatomia de um README moderno, badges e diagramas Mermaid nativos no GitHub | Dois diagramas Mermaid prontos para colar |
| **04** · Docstrings, type hints e IA | Os três estilos canônicos, PEP 484/585/604/695 e uso de IA com segurança | Comparador de estilos de docstring |
| **05** · MLflow + método STAR | MLflow como documento científico · narrativa STAR para o vídeo de entrega | Cards por seção · divisores visuais |
| **06** · Checklist Tech Challenge | Os 6 erros comuns em entregas + checklist persistente no navegador | Grid de erros · Checklist com `localStorage` |

**Stack visual:** HTML + Tailwind CDN + Alpine.js + Mermaid + Prism.js · tudo estático, sem build step.

## Quickstart

### Opção 1 — Makefile

```bash
make serve      # servidor em primeiro plano (Ctrl+C para parar)
# ou
make start      # servidor em background
make open       # abre o textbook no navegador
make stop       # para o servidor em background
```

Por padrão, sobe em [http://localhost:8765](http://localhost:8765).

### Opção 2 — Python direto

```bash
cd textbook && python3 -m http.server 8765
```

Depois abra [http://localhost:8765/index.html](http://localhost:8765/index.html).

## Estrutura do Repositório

```
documentacao-ml/
├── textbook/
│   ├── index.html                 # homepage com cards dos 6 capítulos
│   ├── assets/
│   │   ├── style.css              # design system (DM Sans + DM Serif + paleta creme/roxo)
│   │   └── main.js                # helpers: sidebar, progresso, scroll-spy
│   └── capitulos/
│       ├── 01-importancia-documentacao.html
│       ├── 02-model-cards.html
│       ├── 03-readme-mermaid.html
│       ├── 04-docstrings-type-hints.html
│       ├── 05-mlflow-star.html
│       └── 06-checklist-tech-challenge.html
├── Makefile                       # atalhos para servir o textbook
└── README.md                      # este arquivo
```

## Comandos Disponíveis

```bash
make help       # lista todos os alvos
make serve      # sobe em primeiro plano na porta 8765
make start      # sobe em background e salva PID
make stop       # para o servidor em background
make restart    # reinicia em background
make status     # mostra se está rodando
make open       # abre o browser no textbook
make clean      # remove PID file e artefatos de preview
```

Variáveis configuráveis: `PORT` (padrão `8765`), `HOST` (`localhost`), `DIR` (`textbook`).

Exemplo: `make start PORT=3000`

## Persistência Local

Alguns interativos salvam estado no `localStorage` do navegador:

- Progresso de leitura (quais capítulos foram visitados) — visível na sidebar e no index.
- Checklist do capítulo 6 (`tc-checklist-state`) — 25 itens em 5 frentes.
- Estado da sidebar recolhida (`tb_sidebar_collapsed`).

Para resetar, use o botão "Resetar progresso" na homepage ou limpe os dados do site no navegador.

## Stack e dependências

Todas via CDN — nenhum build step necessário:

| Camada | Biblioteca |
|--------|------------|
| Layout | Tailwind CSS |
| Reatividade | Alpine.js |
| Tipografia | DM Serif Display + DM Sans + JetBrains Mono (Google Fonts) |
| Diagramas | Mermaid v11 |
| Syntax highlight | Prism.js |
| Ícones | Lucide |
