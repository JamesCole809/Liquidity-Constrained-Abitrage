# Liquidity-Constrained Arbitrage: Evidence from a Dual-Listed Stock

This repository contains the code and data processing scripts for the paper  
**"Liquidity-Constrained Arbitrage: Evidence from a Dual-Listed Stock"**.

## LinkedIn
LinkedIn ~~ [LinkedIn](https://www.linkedin.com/in/jamescole05/)

## Overview
The project explores arbitrage opportunities between Royal Dutch Shell’s dual listings on the London Stock Exchange (SHEL.L) and Euronext Amsterdam (SHELL.AS).  
Using minute-level data from Yahoo Finance and a quadratic liquidity cost model, the study shows how market frictions limit arbitrage intensity even when visible mispricings persist.

## Contents
- `arbitrage_analysis.py` — Python script to download data, align listings, and compute spreads, optimal trades, and profits.
- `dual_list_results.csv` — Processed results (example output).
- Figures (`bps_series.png`, `scatter_qstar.png`, `profit_hist.png`) — Plots generated for the paper.
- `paper.tex` — LaTeX source of the research paper.

## Data
All financial data were obtained from [Yahoo Finance](https://finance.yahoo.com/) using the `yfinance` Python package.

