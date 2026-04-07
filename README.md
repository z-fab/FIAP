# FIAP PosTech — Machine Learning Engineering

Repositório com projetos e materiais desenvolvidos durante a pós-graduação (PosTech) em **Machine Learning Engineering** da FIAP.

## Projetos

| Projeto                                     | Descrição                                                                                                                                                                                                                    |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [teste-hipotese](./teste-hipotese/)         | Teste de Hipótese aplicado à avaliação e comparação de modelos de ML. Inclui apostila interativa, pipeline de treinamento com grid search, tracking com MLflow e comparação estatística entre modelos.                       |
| [deploy-agentes-llm](./deploy-agentes-llm/) | Como transformar um agente funcional em um serviço confiável, resiliente e deployável, passando por três padrões de comunicação e controles de produção. Inclui apostila interativa e implementação de casos de uso          |
| [agentes-langgraph](./agentes-langgraph/)   | Implementa três padrões distintos de agentes com [LangGraph](https://langchain-ai.github.io/langgraph/), cada um demonstrando uma abordagem arquitetural diferente: prebuilt simplificado, ReAct manual e Human-in-the-Loop. |

## Tecnologias Utilizadas

- Python 3.10+
- Scikit-learn, PyTorch
- MLflow (experiment tracking & model registry)
- Pandas, NumPy, SciPy, Statsmodels
- Jupyter Notebooks
- Docker

## Estrutura

Cada projeto está em seu próprio diretório com README dedicado, dependências isoladas e instruções de execução.

```
repositorio/
├── teste-hipotese/    # Teste de Hipótese em ML
└── ...                # Próximos projetos
```

## Como Usar

Navegue até o diretório do projeto desejado e siga as instruções do README correspondente.

```bash
cd teste-hipotese
make setup
```
