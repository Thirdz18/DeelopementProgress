# GoodMarket

A Web3 Learn & Earn platform built on the GoodDollar ecosystem. Users earn G$ tokens on the Celo network through educational quizzes, social media tasks, minigames, and community engagement.

## Run & Operate

- `gunicorn --config gunicorn.conf.py main:app` — start the app (port 5000)
- The workflow "Start application" runs this automatically

## Stack

- **Backend:** Python 3.12, Flask, Gunicorn (gthread workers)
- **Frontend:** Server-side rendered Jinja2 templates + static assets
- **Database:** Supabase (PostgreSQL)
- **Blockchain:** Web3.py, Celo network, GoodDollar (G$) contracts
- **WalletConnect:** Node.js sidecar (`wc_service.js`, port 3001)

## Where things live

- `main.py` — Flask app entry point, initializes all services and blueprints
- `routes.py` — Core API routes and auth decorators
- `blockchain.py` — Blockchain logic (UBI claims, G$ balances)
- `config.py` — Global configuration and reward settings
- `supabase_client.py` — Database connection and utilities
- `gunicorn.conf.py` — Gunicorn server config (reads `PORT` env var)
- `templates/` — Jinja2 HTML templates (30 pages)
- `static/` — Static assets (JS bundles, icons, manifest)
- `learn_and_earn/` — Learn & Earn quiz module
- `minigames/` — Minigames module
- `savings/` — G$ Savings module
- `p2p_trading/` — P2P trading module
- `contracts/` — Solidity smart contracts and deployment scripts

## Required Secrets

The app gracefully degrades when these are missing, but full functionality requires:
- `SUPABASE_URL` + `SUPABASE_KEY` — database
- `SUPABASE_SERVICE_ROLE_KEY` — admin operations
- `COMMUNITY_KEY` — community stories blockchain key
- `MERCHANT_ADDRESS` + `GAMES_KEY` — minigames
- `WALLETCONNECT_PROJECT_ID` — WalletConnect sidecar
- `RELOADLY_CLIENT_ID` + `RELOADLY_CLIENT_SECRET` — gift cards
- `LEARN_EARN_WALLET` — Learn & Earn rewards wallet

## Gotchas

- The app starts with many warnings about missing env vars — this is expected; features degrade gracefully
- `gunicorn.conf.py` reads `PORT` from environment; default is 5000
- WalletConnect sidecar (`wc_service.js`) is started automatically by `main.py` when `WALLETCONNECT_PROJECT_ID` is set

## User preferences

_Populate as needed._
