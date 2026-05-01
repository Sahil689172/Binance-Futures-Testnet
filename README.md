# 🤖 Binance Futures Testnet Trading Bot

A clean, production-grade Python CLI trading bot for **Binance Futures Testnet (USDT-M)**.  
Supports Market, Limit, and Stop-Market orders with structured logging, full input validation, and proper error handling.

---

## ✨ Features

| Feature | Detail |
|---|---|
| Order types | MARKET · LIMIT · STOP\_MARKET (bonus) · TAKE\_PROFIT\_MARKET (bonus) |
| Order sides | BUY and SELL |
| CLI | argparse — typed, validated, documented |
| Logging | Rotating file (DEBUG) + console (INFO) — all requests/responses captured |
| Error handling | API errors · network failures · input validation · typed exceptions |
| Auth | HMAC-SHA256 signed requests (no third-party SDK required) |
| Structure | Separated `client` / `orders` / `validators` / `logging_config` layers |

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # package marker
│   ├── client.py            # Binance REST client (signing, HTTP, error handling)
│   ├── orders.py            # order placement logic + result formatting
│   ├── validators.py        # pure input validation (no I/O)
│   └── logging_config.py   # rotating file + console logging setup
├── cli.py                   # CLI entry point (argparse sub-commands)
├── logs/
│   └── trading_bot.log      # sample log file (auto-created on first run)
├── .env.example             # template for API credentials
├── requirements.txt
└── README.md
```

---

## 🚀 Setup

### 1. Get Binance Futures Testnet API Keys

1. Go to **[https://testnet.binancefuture.com](https://testnet.binancefuture.com)**
2. Log in (or register) — a GitHub OAuth account is accepted
3. Navigate to **API Key** tab
4. Click **Generate** — copy your **API Key** and **Secret Key** immediately (the secret is shown only once)

### 2. Clone / extract the project

```bash
unzip trading_bot.zip     # or: git clone <repo-url>
cd trading_bot
```

### 3. Create a virtual environment & install dependencies

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 4. Set API credentials

**Option A — Environment variables (recommended)**

```bash
# macOS / Linux
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"

# Windows (Command Prompt)
set BINANCE_API_KEY=your_testnet_api_key
set BINANCE_API_SECRET=your_testnet_api_secret

# Windows (PowerShell)
$env:BINANCE_API_KEY="your_testnet_api_key"
$env:BINANCE_API_SECRET="your_testnet_api_secret"
```

**Option B — `.env` file**

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

Then load it before running (Linux/macOS):
```bash
export $(cat .env | xargs)
```

**Option C — CLI flags** *(not recommended for production — visible in shell history)*

```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET place ...
```

---

## 🖥️ Usage

All commands follow the pattern:

```
python cli.py [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

### Global options

| Flag | Description |
|---|---|
| `--api-key KEY` | Binance API key (or env var `BINANCE_API_KEY`) |
| `--api-secret SECRET` | Binance API secret (or env var `BINANCE_API_SECRET`) |
| `--log-level LEVEL` | Console verbosity: `DEBUG` / `INFO` / `WARNING` / `ERROR` (default: `INFO`) |

---

### `ping` — Test connectivity

```bash
python cli.py ping
```

Expected output:
```
✅  Testnet is reachable — server time: 1745831642413 ms
```

---

### `place` — Place an order

```
python cli.py place --symbol SYMBOL --side BUY|SELL --type TYPE --qty QTY [--price P] [--stop-price SP]
```

#### MARKET order — BUY

```bash
python cli.py place \
  --symbol BTCUSDT \
  --side   BUY \
  --type   MARKET \
  --qty    0.001
```

#### MARKET order — SELL

```bash
python cli.py place \
  --symbol BTCUSDT \
  --side   SELL \
  --type   MARKET \
  --qty    0.001
```

#### LIMIT order — BUY

```bash
python cli.py place \
  --symbol BTCUSDT \
  --side   BUY \
  --type   LIMIT \
  --qty    0.001 \
  --price  90000
```

#### LIMIT order — SELL

```bash
python cli.py place \
  --symbol BTCUSDT \
  --side   SELL \
  --type   LIMIT \
  --qty    0.001 \
  --price  98000
```

#### STOP_MARKET order — SELL (stop-loss) *(Bonus)*

```bash
python cli.py place \
  --symbol     BTCUSDT \
  --side       SELL \
  --type       STOP_MARKET \
  --qty        0.001 \
  --stop-price 89000
```

#### TAKE_PROFIT_MARKET — SELL *(Bonus)*

```bash
python cli.py place \
  --symbol     BTCUSDT \
  --side       SELL \
  --type       TAKE_PROFIT_MARKET \
  --qty        0.001 \
  --stop-price 100000
```

**Sample output:**

```
────────────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────────
  Symbol            : BTCUSDT
  Side              : BUY
  Order Type        : MARKET
  Quantity          : 0.001
────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────
  ORDER RESPONSE
────────────────────────────────────────────────────────────
  Order ID          : 4253891023
  Client Order ID   : web_9E6EjqZxpHIpYqxBqFmL
  Symbol            : BTCUSDT
  Status            : FILLED
  Side              : BUY
  Type              : MARKET
  Orig Qty          : 0.001
  Executed Qty      : 0.001
  Avg Price         : 93412.50000
────────────────────────────────────────────────────────────

✅  Order placed successfully!
```

---

### `orders` — List open orders

```bash
# All open orders
python cli.py orders

# Filtered by symbol
python cli.py orders --symbol BTCUSDT
```

---

### `cancel` — Cancel an order

```bash
python cli.py cancel --symbol BTCUSDT --order-id 4253894502
```

---

### `account` — View account balances

```bash
python cli.py account
```

---

## 📋 Supported Symbols

Common USDT-M Futures symbols:

`BTCUSDT` · `ETHUSDT` · `BNBUSDT` · `XRPUSDT` · `SOLUSDT` · `ADAUSDT` · `DOGEUSDT` · `AVAXUSDT` · `DOTUSDT` · `MATICUSDT`

Other valid symbols will work too — the validator will warn but allow them through to the API.

---

## 📝 Logging

Logs are written to `logs/trading_bot.log` automatically (rotating, max 5 MB × 3 backups).

| Channel | Level | Content |
|---|---|---|
| File | DEBUG | Every request/response pair, signatures redacted |
| Console | INFO (configurable) | Human-readable order events & errors |

To enable verbose console output:

```bash
python cli.py --log-level DEBUG place ...
```

---

## ⚠️ Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API credentials | Descriptive error + exit(1) |
| Invalid symbol / side / type | Validation error printed before any API call |
| Missing required price/stop price | Validation error with guidance |
| Binance API error (e.g. -1111) | Error code + message logged and printed |
| Network timeout / connection refused | Friendly message + exit(1) |

---

## 🔧 Assumptions

1. **Testnet only** — the base URL is hardcoded to `https://testnet.binancefuture.com`. To switch to mainnet, change `BASE_URL` in `bot/client.py` (use real funds at your own risk).
2. **One-way mode** — orders are placed with `positionSide=BOTH` (Binance default). Hedge mode is not configured.
3. **Quantity/price precision** — sensible defaults are applied per-symbol. For production use the `/fapi/v1/exchangeInfo` filters.
4. **No persistence** — the bot is stateless; order IDs must be tracked externally if needed.
5. **Python ≥ 3.8** required (uses `from __future__ import annotations`).

---

## 🧪 Running Tests

No external test framework is required. To do a quick smoke test:

```bash
# 1. Verify connectivity
python cli.py ping

# 2. Check your account balance
python cli.py account

# 3. Place a small market buy
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# 4. Place a limit sell (resting order)
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 99999

# 5. List open orders to confirm it's there
python cli.py orders --symbol BTCUSDT

# 6. Cancel it
python cli.py cancel --symbol BTCUSDT --order-id <ORDER_ID_FROM_STEP_4>
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `requests` | ≥ 2.31.0 | HTTP client for Binance REST API |

Standard library only otherwise (`hashlib`, `hmac`, `argparse`, `logging`, `decimal`, `time`).

---

## 👤 Author

Built for the **Python Developer (Trading Bot)** application task.  
Testnet base URL: `https://testnet.binancefuture.com`
