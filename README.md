# GoodMarket

A Web3 earning platform on the GoodDollar ecosystem. Users earn G$ tokens on the Celo network through quizzes, social tasks, minigames, and community engagement.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, Flask, Gunicorn |
| Frontend | Jinja2 templates, static assets |
| Database | Supabase (PostgreSQL) |
| Blockchain | Web3.py, Celo network, GoodDollar (G$) |
| Wallet | WalletConnect (Node.js sidecar on port 3001) |
| Package Manager | `uv` (Python), `npm` (Node.js) |

---

## Project Structure

### Core Files
| Path | Description |
|------|-------------|
| `main.py` | Flask app entry point |
| `routes.py` | API routes and auth decorators |
| `blockchain.py` | UBI claims, G$ balances |
| `config.py` | Global configuration and rewards |
| `supabase_client.py` | Database connection |
| `gunicorn.conf.py` | Server config (port 5000) |
| `wc_service.js` | WalletConnect service (port 3001) |

### Modules
| Path | Description |
|------|-------------|
| `learn_and_earn/` | Quiz module with streaming payout support |
| `minigames/` | Game rewards |
| `twitter_task/` | Twitter social tasks |
| `telegram_task/` | Telegram social tasks |
| `discourse_task/` | Forum task rewards |
| `savings/` | G$ Savings vault (v5) |
| `community_stories/` | Community content rewards |
| `jumble/` | Word game |
| `referral_program/` | Referral system |

### Smart Contracts
| Path | Description |
|------|-------------|
| `contracts/GDSavings.sol` | Savings vault deployed on Celo |
| `contracts/deploy_savings_contract.py` | Deployment script |

---

## Getting Started

### Run Locally
```bash
uv run gunicorn --config gunicorn.conf.py main:app
```
- App runs on port **5000**
- WalletConnect sidecar auto-starts if `WALLETCONNECT_PROJECT_ID` is set

### Required Environment Variables
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase API key |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side only (file uploads) |
| `SECRET_KEY` | Flask session secret |
| `WALLETCONNECT_PROJECT_ID` | WalletConnect project ID |
| `CELO_RPC_URL` | Celo RPC (default: `https://forno.celo.org`) |
| `GOODDOLLAR_CONTRACT` | GoodDollar token address |
| `GAMES_KEY` | Minigame transactions key |
| `COMMUNITY_KEY` | Community stories rewards key |
| `PRODUCTION_DOMAIN` | Production domain |

### Learn & Earn Streaming (Optional)
Enable Superfluid streaming for quiz rewards:
- `LEARN_EARN_PAYOUT_MODE` — `instant` (default) or `streaming` variants
- `LEARN_EARN_STREAM_TOKEN_ADDRESS` — GoodDollar SuperToken address
- `SUPERFLUID_HOST_ADDRESS` — Superfluid Host contract
- `SUPERFLUID_CFA_V1_ADDRESS` — Constant Flow Agreement v1

Apply `sql/learn_earn_streaming_payouts.sql` migration before enabling.

---

## Features

### UBI Claim + Gas Fallback
Safe sequence before sending `claim()` to prevent wasted gas:
1. Check entitlement (`isWhitelisted` + `checkEntitlement`)
2. Check gas readiness
3. Top-up via GoodServer API → on-chain fallback via `GAMES_KEY`
4. Poll balance → prompt user to approve `claim()`

### Daily Voucher
- Admin sets payment link at Admin Dashboard
- Appears daily at **2PM PHT** (UTC+8)
- First user to claim gets it (instant disappear for others)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/voucher/daily` | User | Get active voucher |
| `POST /api/voucher/claim` | User | Claim voucher |
| `GET/POST /api/admin/voucher` | Admin | Get/set voucher |
| `POST /api/admin/voucher/reset` | Admin | Reset claim status |

### Feature Visibility
Admins can show/hide `/swap` and `/wallet` pages via `maintenance_settings` table.

---

## Deployment

### Replit Autoscale
```bash
gunicorn --config gunicorn.conf.py main:app
```

### Vercel
- Uses `@vercel/python`
- WalletConnect skipped (browser fallback used)
- All env vars in Vercel dashboard

---

## Savings v5 — Custom Lock Days & USDT

**Key Changes from v4:**
- Lock duration: **1–360 days** (saver chooses)
- Tokens: G$, CELO, cUSD, **USDT**
- Bonus tiers recalculated for flexible locks

| Token | Min | Max |
|-------|-----|-----|
| G$ | 1,000 | 10,000,000 |
| CELO | 1 | 100,000 |
| cUSD | 1 | 1,000,000 |
| USDT | 1 | 1,000,000 |

### Deploy
```bash
uv run python contracts/deploy_savings_contract.py
```

After deploy, update:
1. `SAVINGS_CONTRACT_ADDRESS`
2. `LEGACY_V4_CONTRACT_ADDRESS` (for read-only v4 panel)
3. `USDT_TOKEN_ADDRESS`
4. `SAVINGS_DEPLOYMENT_BLOCK` in `templates/savings.html`
