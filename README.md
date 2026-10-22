# portfolio-decision-engine
Public example of a personal portfolio tracking and analytics project using Cloudflare Workers, Cloudflare KV, Python, and Google Gemini.

This repository is a shareable, non-live version of a private project. It contains no credentials and does not work with a real portfolio until you configure your own private services and secrets. It is an example, not a production-ready financial product or investment advice.

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

No credentials or live services are needed to browse this example. The scheduled GitHub Actions workflows are disabled unless the repository variable `ENABLE_LIVE_WORKFLOWS` is explicitly set to `true`.

For private, personal use only:

1. Copy `.env.example` to `.env` and fill in your own local credentials. Keep `.env` and `holdings.yaml` private; never commit real values or portfolio data.
2. Copy `holdings.example.yml` to `holdings.yaml` and replace the sample entries with your own data. The real `holdings.yaml` is ignored by Git.
3. Deploy `worker.js` from a private Worker project or paste it into your private Cloudflare Worker. Bind a KV namespace as `PORTFOLIO_STORE` and set the Worker secrets `PORTFOLIO_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `TELEGRAM_WEBHOOK_SECRET`. Configure the Telegram webhook with the Worker URL and matching `secret_token`.
4. To deliberately enable scheduled workflows in a private GitHub repository, set the repository variable `ENABLE_LIVE_WORKFLOWS` to `true`, set `PORTFOLIO_API_URL` as a repository variable, and add the `PORTFOLIO_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `GEMINI_API_KEY` repository secrets. The Cloudflare and GitHub `PORTFOLIO_API_TOKEN` values must match.

If real portfolio data was committed before this public example was prepared, deleting the file in a later commit does not remove it from Git history. Treat previously published private data as exposed and review the repository history separately.

Portfolio price reports show the Yahoo Finance closing-price date. Data older than seven calendar days is marked with a stale-price warning.