# portfolio-decision-engine
Event-driven, low-latency personal portfolio tracking and analytics bot using Cloudflare Workers, Cloudflare KV, Python, and Google Gemini.
# Serverless Multi-Asset Portfolio Tracker & Decision Support Engine

An event-driven, zero-maintenance personal portfolio tracker and financial decision support system built on a hybrid serverless architecture.

## 🚀 Key Highlights & Architecture

- **Low-Latency Edge CRUD:** Powered by **Cloudflare Workers** and **Workers KV** for sub-50ms execution of portfolio operations (`/al`, `/sat`, `/yatir`, `/cek`, `/gecmis`) via Telegram Webhooks.
- **Serverless Analytics & Caching:** **GitHub Actions** runs scheduled headless Python cron jobs that extract live market data via **Yahoo Finance** & **TCMB (Central Bank of Turkey)** APIs, compute risk/rebalancing deviations against constraints, and warm the edge KV cache for instantaneous `/kar` and `/rapor` retrieval.
- **LLM-Powered News Curation:** Ingests live RSS streams across local/global financial outlets and leverages Google **Gemini** with prompt engineering to deliver noise-filtered morning executive briefs based on compliance rules.

                  +---------------------------------------+
                  |             Telegram User             |
                  +-------------------+-------------------+
                                      |
                    Webhook / Commands| (Instant CRUD & Fast Reads)
                                      v
+-------------------+        +------------+-------------+
|   GitHub Actions  |        |    Cloudflare Worker     |
|   (Cron Jobs)     |        |    (Edge Router & API)   |
+---------+---------+        +------------+-------------+
|                               |
| Cache Precomputed Analysis    | Read/Write State
+---------------------->+-------v-------+
| Cloudflare KV |
| (Global State)|
+---------------+


## 🛠️ Tech Stack

- **Edge & Serverless:** Cloudflare Workers, Cloudflare KV
- **Automation & CI/CD:** GitHub Actions (Cron Workflows)
- **Data & Analytics:** Python 3.11, Pandas, yfinance, PyYAML
- **Generative AI:** Google Gemini SDK (`google-genai`)
- **Interface:** Telegram Bot API (HTML & Markdown formatting)

## 📋 Features

1. **Portfolio State Machine:** Automated weighted average cost calculation, multi-currency support (TRY & USD), and liquidity pool tracking.
2. **Dynamic Rebalancing Engine:** Real-time deviation alerts against target asset allocation boundaries defined in `constraints.yaml`.
3. **Audit Log:** Chronological transaction journal with timestamped change histories.
4. **Resilient Data Fallback:** Multi-tier fallback strategy (Cloudflare KV -> Local YAML fallback; TCMB XML -> Yahoo Finance v8 API fallback).

## ⚙️ Setup & Configuration

1. Copy `.env.example` to `.env` and supply your credentials:
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
   - `PORTFOLIO_API_URL`
2. Deploy the Worker using Cloudflare Dashboard or Wrangler CLI.
3. Configure GitHub Repository Secrets with the same keys to activate automated background caching.