import datetime
import os
import re
import sqlite3

from flask import Flask, jsonify, redirect, render_template, request, url_for
from web3 import Web3

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# Example:
# https://sepolia.infura.io/v3/YOUR_API_KEY
# https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
RPC_URL = os.environ.get("RPC_URL")

CONTRACT_ADDRESS = Web3.to_checksum_address(
    os.environ.get(
        "CONTRACT_ADDRESS",
        "0xab32bd19c1a369b9a949aa7ff2bd0ef5a2518b76",
    )
)

# Network the contract lives on (default: Sepolia). MetaMask is asked to
# switch to this chain before sending a transaction.
CHAIN_ID = int(os.environ.get("CHAIN_ID", 11155111))
CHAIN_NAME = os.environ.get("CHAIN_NAME", "Sepolia")
EXPLORER_URL = os.environ.get("EXPLORER_URL", "https://sepolia.etherscan.io")

ABI = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "_number",
                "type": "uint256"
            }
        ],
        "name": "set",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "get",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "storedNumber",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


# ---------- Database (SQLite, same approach as the main branch) ----------
# One local file. Each request opens a connection, runs its SQL, commits and
# closes it again.
DB_PATH = os.environ.get("DB_PATH", "history.db")


def init_db():
    """Create the history table the first time the app starts."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS history "
        "(wallet text, number text, tx_hash text, timestamp timestamp)"
    )
    conn.commit()
    c.close()
    conn.close()


init_db()


def get_contract():
    """Return a read-only contract instance, or None if RPC is unavailable."""
    if not RPC_URL:
        return None

    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 10}))
    return w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)


def read_stored_number():
    """Call get() on the contract. Returns None on any failure."""
    contract = get_contract()
    if contract is None:
        return None

    try:
        return contract.functions.get().call()
    except Exception as error:
        app.logger.warning("Could not read contract: %s", error)
        return None


@app.route("/")
def index():
    return render_template(
        "index.html",
        current_number=read_stored_number(),
        contract_address=CONTRACT_ADDRESS,
        abi=ABI,
        rpc_configured=bool(RPC_URL),
        chain_id=CHAIN_ID,
        chain_name=CHAIN_NAME,
        explorer_url=EXPLORER_URL.rstrip("/"),
    )


@app.route("/api/number")
def api_number():
    number = read_stored_number()

    if number is None:
        return jsonify({"error": "Unable to read the contract."}), 503

    # Return as a string so large uint256 values are not rounded by JavaScript.
    return jsonify({"number": str(number)})


@app.route("/api/history", methods=["POST"])
def api_add_history():
    """Called by the frontend after a set() transaction is confirmed."""
    data = request.get_json(silent=True) or {}
    wallet = str(data.get("wallet", ""))
    number = str(data.get("number", ""))
    tx_hash = str(data.get("tx_hash", ""))

    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", wallet):
        return jsonify({"error": "Invalid wallet address."}), 400
    if not re.fullmatch(r"\d+", number):
        return jsonify({"error": "Invalid number."}), 400
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash):
        return jsonify({"error": "Invalid transaction hash."}), 400

    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO history (wallet, number, tx_hash, timestamp) VALUES (?,?,?,?)",
        (wallet, number, tx_hash, time),
    )
    conn.commit()
    c.close()
    conn.close()
    return jsonify({"ok": True})


@app.route("/history", methods=["GET", "POST"])
def history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT wallet, number, tx_hash, timestamp FROM history ORDER BY timestamp DESC")
    rows = c.fetchall()
    c.close()
    conn.close()
    return render_template(
        "history.html",
        rows=rows,
        explorer_url=EXPLORER_URL.rstrip("/"),
        cleared=request.args.get("cleared") == "1",
    )


@app.route("/deleteHistory", methods=["POST"])
def delete_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM history")
    conn.commit()
    c.close()
    conn.close()
    return redirect(url_for("history", cleared=1))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
