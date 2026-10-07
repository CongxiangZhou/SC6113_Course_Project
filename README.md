# SC6113-Class-Example-ChatGPT

A minimal Flask + HTML + CSS DApp for a `SimpleStorage` smart contract.

- Contract: `0xab32bd19c1a369b9a949aa7ff2bd0ef5a2518b76`
- **Read** (`get()`): Flask calls the contract through `RPC_URL` (falls back to MetaMask).
- **Write** (`set(uint256)`): signed in the browser by the user's MetaMask wallet.
  The server never holds a private key.

## Database (this branch)

Every confirmed `set()` transaction is also saved to a local **SQLite** database,
using the same `sqlite3` approach as the `main` branch (open a connection,
execute, commit, close in each route).

- File: `history.db` (created automatically on first run; path can be changed with `DB_PATH`)
- Table: `history (wallet text, number text, tx_hash text, timestamp timestamp)`
- `POST /api/history` — the frontend calls this after `tx.wait()` succeeds
- `GET /history` — page listing all records, with explorer links
- `POST /deleteHistory` — clears the table

Note: the blockchain stays the source of truth for the stored number; the
database is an off-chain log, so its records are only as trustworthy as the
client that sent them.

## Project structure

```
app.py               Flask backend (reads the contract via web3.py)
requirements.txt
Procfile             gunicorn entry point for cloud hosts
templates/index.html Frontend (ethers.js + MetaMask)
templates/history.html History page (reads from SQLite)
static/styles.css
```

## Run locally

```bash
pip install -r requirements.txt
export RPC_URL="https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY"
python app.py
```

Open http://localhost:5000. Make sure MetaMask is on the same network the contract is deployed to.

## Environment variables

| Name               | Required | Description                                      |
|--------------------|----------|--------------------------------------------------|
| `RPC_URL`          | yes      | RPC endpoint of the network the contract is on   |
| `CONTRACT_ADDRESS` | no       | Override the default contract address            |
| `SECRET_KEY`       | no       | Flask secret key                                 |
| `PORT`             | no       | Port for `python app.py` (default 5000)          |
| `DB_PATH`          | no       | SQLite file path (default `history.db`)          |

Do not commit your RPC API key — set it as an environment variable on your host.

## Deploy (Render / Railway)

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app` (already in `Procfile`)
- Add `RPC_URL` in the service's environment settings.
