"""Ferramentas do agente financeiro.

Integra com APIs reais para consulta de cotações (AwesomeAPI),
dados de ações (yfinance) e cálculos de retorno.
"""

import httpx
import yfinance as yf
from langchain_core.tools import tool


@tool
def consultar_cotacao_moeda(moeda: str) -> str:
    """Consulta a cotação atual de uma moeda em relação ao Real (BRL).

    Utiliza a AwesomeAPI (economia.awesomeapi.com.br) para obter dados
    de câmbio em tempo real. Retorna preço atual, máxima, mínima e
    variação percentual do dia.

    Args:
        moeda: Código da moeda de origem, ex: USD, EUR, GBP, BTC.

    Returns:
        String formatada com cotação atual e informações do dia.
    """
    par = f"{moeda.upper()}-BRL"
    url = f"https://economia.awesomeapi.com.br/json/last/{par}"

    try:
        with httpx.Client(timeout=10.0) as client:
            resposta = client.get(url)
            resposta.raise_for_status()
            dados = resposta.json()
    except httpx.TimeoutException:
        return f"Erro: tempo limite excedido ao consultar cotação de {moeda}."
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Moeda '{moeda}' não encontrada. Verifique o código (ex: USD, EUR, GBP)."
        return f"Erro ao consultar cotação de {moeda}: status HTTP {e.response.status_code}."
    except Exception as e:
        return f"Erro inesperado ao consultar cotação de {moeda}: {e}"

    chave = par.replace("-", "")
    if chave not in dados:
        return f"Dados de cotação não disponíveis para {moeda}."

    info = dados[chave]
    try:
        preco_atual = float(info["bid"])
        maximo = float(info["high"])
        minimo = float(info["low"])
        variacao_pct = float(info["pctChange"])
        nome = info.get("name", par)

        sinal = "+" if variacao_pct >= 0 else ""
        return (
            f"Cotação {nome} ({moeda}/BRL)\n"
            f"  Preço atual : R$ {preco_atual:,.4f}\n"
            f"  Máxima do dia: R$ {maximo:,.4f}\n"
            f"  Mínima do dia: R$ {minimo:,.4f}\n"
            f"  Variação hoje: {sinal}{variacao_pct:.2f}%"
        )
    except (KeyError, ValueError) as e:
        return f"Erro ao processar dados de {moeda}: {e}"


@tool
def consultar_cotacao_acao(ticker: str) -> str:
    """Consulta o preço atual de uma ação via yfinance.

    Retorna preço atual, fechamento anterior, variação percentual do dia
    e volume negociado. Para ações brasileiras, adicione '.SA' ao ticker
    (ex: PETR4.SA, VALE3.SA).

    Args:
        ticker: Código da ação, ex: AAPL, PETR4.SA, VALE3.SA.

    Returns:
        String formatada com preço atual e indicadores do dia.
    """
    try:
        ativo = yf.Ticker(ticker.upper())
        info = ativo.fast_info
    except Exception as e:
        return f"Erro ao acessar dados de {ticker}: {e}"

    try:
        preco_atual = info.last_price
        fechamento_anterior = info.previous_close
        volume = info.last_volume

        if preco_atual is None or fechamento_anterior is None:
            return f"Dados de preço indisponíveis para '{ticker}'. Verifique o ticker."

        variacao = preco_atual - fechamento_anterior
        variacao_pct = (variacao / fechamento_anterior) * 100
        sinal = "+" if variacao >= 0 else ""

        # Detecta moeda (ações brasileiras são em BRL)
        moeda_simbolo = "R$" if ticker.upper().endswith(".SA") else "$"

        return (
            f"Cotação {ticker.upper()}\n"
            f"  Preço atual       : {moeda_simbolo} {preco_atual:,.2f}\n"
            f"  Fechamento anterior: {moeda_simbolo} {fechamento_anterior:,.2f}\n"
            f"  Variação hoje     : {sinal}{variacao:,.2f} ({sinal}{variacao_pct:.2f}%)\n"
            f"  Volume            : {int(volume):,}"
        )
    except AttributeError:
        return f"Ticker '{ticker}' não encontrado ou sem dados disponíveis."
    except Exception as e:
        return f"Erro ao processar dados de {ticker}: {e}"


@tool
def calcular_retorno_acao(ticker: str, dias: int) -> str:
    """Calcula o retorno histórico de uma ação em um período determinado.

    Busca dados históricos via yfinance e calcula o retorno percentual,
    preço inicial, preço final e o ganho ou perda por lote de 100 ações.

    Args:
        ticker: Código da ação, ex: AAPL, PETR4.SA. Para ações brasileiras
                use sufixo .SA (ex: PETR4.SA).
        dias: Número de dias úteis a considerar no período histórico.

    Returns:
        String formatada com análise de retorno do período.
    """
    if dias <= 0:
        return "O número de dias deve ser maior que zero."

    try:
        ativo = yf.Ticker(ticker.upper())
        historico = ativo.history(period=f"{dias}d")
    except Exception as e:
        return f"Erro ao buscar histórico de {ticker}: {e}"

    if historico.empty:
        return f"Sem dados históricos para '{ticker}' nos últimos {dias} dias."

    try:
        preco_inicial = float(historico["Close"].iloc[0])
        preco_final = float(historico["Close"].iloc[-1])
        data_inicial = historico.index[0].strftime("%d/%m/%Y")
        data_final = historico.index[-1].strftime("%d/%m/%Y")

        retorno_pct = ((preco_final - preco_inicial) / preco_inicial) * 100
        ganho_por_lote = (preco_final - preco_inicial) * 100  # lote de 100 ações

        sinal = "+" if retorno_pct >= 0 else ""
        moeda_simbolo = "R$" if ticker.upper().endswith(".SA") else "$"
        resultado_lote = "Ganho" if ganho_por_lote >= 0 else "Perda"

        return (
            f"Retorno histórico {ticker.upper()} — últimos {dias} dias\n"
            f"  Período       : {data_inicial} → {data_final}\n"
            f"  Preço inicial : {moeda_simbolo} {preco_inicial:,.2f}\n"
            f"  Preço final   : {moeda_simbolo} {preco_final:,.2f}\n"
            f"  Retorno       : {sinal}{retorno_pct:.2f}%\n"
            f"  {resultado_lote} por lote (100 ações): "
            f"{moeda_simbolo} {abs(ganho_por_lote):,.2f}"
        )
    except Exception as e:
        return f"Erro ao calcular retorno de {ticker}: {e}"


@tool
def comparar_acoes(tickers: list[str], dias: int) -> str:
    """Compara o desempenho de múltiplas ações em um período histórico.

    Busca dados históricos de cada ação via yfinance, calcula o retorno
    percentual de cada uma e identifica a melhor e a pior performance
    no período informado.

    Args:
        tickers: Lista de códigos de ações, ex: ["AAPL", "MSFT", "GOOGL"]
                 ou ["PETR4.SA", "VALE3.SA"]. Para ações brasileiras use .SA.
        dias: Número de dias úteis a considerar no período histórico.

    Returns:
        String formatada com ranking de desempenho e destaque para melhor
        e pior ação do período.
    """
    if not tickers:
        return "Nenhum ticker informado para comparação."
    if dias <= 0:
        return "O número de dias deve ser maior que zero."

    resultados = []
    erros = []

    for ticker in tickers:
        ticker_upper = ticker.upper()
        try:
            ativo = yf.Ticker(ticker_upper)
            historico = ativo.history(period=f"{dias}d")

            if historico.empty:
                erros.append(f"{ticker_upper}: sem dados para o período")
                continue

            preco_inicial = float(historico["Close"].iloc[0])
            preco_final = float(historico["Close"].iloc[-1])
            retorno_pct = ((preco_final - preco_inicial) / preco_inicial) * 100

            resultados.append(
                {
                    "ticker": ticker_upper,
                    "retorno_pct": retorno_pct,
                    "preco_inicial": preco_inicial,
                    "preco_final": preco_final,
                    "moeda": "R$" if ticker_upper.endswith(".SA") else "$",
                }
            )
        except Exception as e:
            erros.append(f"{ticker_upper}: {e}")

    if not resultados:
        msg = "Não foi possível obter dados para nenhum ticker informado."
        if erros:
            msg += "\nErros:\n" + "\n".join(f"  - {e}" for e in erros)
        return msg

    # Ordena do melhor para o pior retorno
    resultados.sort(key=lambda x: x["retorno_pct"], reverse=True)
    melhor = resultados[0]
    pior = resultados[-1]

    linhas = [f"Comparação de ações — últimos {dias} dias\n"]
    linhas.append(f"{'Ticker':<12} {'Início':>10} {'Fim':>10} {'Retorno':>10}")
    linhas.append("-" * 46)

    for r in resultados:
        sinal = "+" if r["retorno_pct"] >= 0 else ""
        linhas.append(
            f"{r['ticker']:<12} "
            f"{r['moeda']} {r['preco_inicial']:>7,.2f} "
            f"{r['moeda']} {r['preco_final']:>7,.2f} "
            f"{sinal}{r['retorno_pct']:>7.2f}%"
        )

    linhas.append("")
    sinal_melhor = "+" if melhor["retorno_pct"] >= 0 else ""
    sinal_pior = "+" if pior["retorno_pct"] >= 0 else ""
    linhas.append(
        f"Melhor desempenho: {melhor['ticker']} ({sinal_melhor}{melhor['retorno_pct']:.2f}%)"
    )
    if len(resultados) > 1:
        linhas.append(
            f"Pior desempenho : {pior['ticker']} ({sinal_pior}{pior['retorno_pct']:.2f}%)"
        )

    if erros:
        linhas.append("\nAvisos:")
        linhas.extend(f"  - {e}" for e in erros)

    return "\n".join(linhas)
