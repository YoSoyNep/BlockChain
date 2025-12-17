from flask import Flask, jsonify, request
from blockchain_core import Blockchain
from uuid import uuid4
import requests

app = Flask(__name__)
node_id = str(uuid4()).replace("-", "")
bc = Blockchain(difficulty_prefix="0000")
bc.nodes = set()

@app.get("/chain")
def get_chain():
    return jsonify({
        "length": len(bc.chain),
        "chain": [b.__dict__ for b in bc.chain],
    })

@app.post("/transactions/new")
def new_transaction():
    data = request.get_json(force=True) or {}
    required = ["sender", "recipient", "amount"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields", "required": required}), 400

    index = bc.new_transaction(data["sender"], data["recipient"], float(data["amount"]))
    return jsonify({"message": f"Transaction will be added to Block {index}"}), 201

@app.get("/mine")
def mine():
    # 1) Mining reward (coinbase tx)
    bc.new_transaction(sender="0", recipient=node_id, amount=1)

    # 2) Proof of Work
    last = bc.last_block
    last_hash = bc.hash(last)
    proof = bc.proof_of_work(last.proof, last_hash, bc.current_transactions)
    block = bc.new_block(proof=proof, previous_hash=last_hash)

    # 3) Yeni blok
    return jsonify({
        "message": "New Block Forged",
        "block": block.__dict__,
        "chain_valid": bc.valid_chain(),
    }), 200

@app.post("/nodes/register")
def register_nodes():
    data = request.get_json(force=True) or {}
    nodes = data.get("nodes")
    if not nodes:
        return jsonify({"error": "Please supply a valid list of nodes"}), 400

    for node in nodes:
        bc.nodes.add(node)

    return jsonify({
        "message": "New nodes have been added",
        "total_nodes": list(bc.nodes),
    }), 201

@app.get("/nodes/resolve")
def consensus():
    replaced = False
    max_length = len(bc.chain)
    new_chain = None

    for node in bc.nodes:
        try:
            r = requests.get(f"{node}/chain", timeout=5)
            if r.status_code != 200:
                continue

            data = r.json()
            length = data["length"]
            chain_data = data["chain"]

            # JSON -> Block objeleri
            from blockchain_core import Block
            chain = [Block(**b) for b in chain_data]

            if length > max_length and bc.valid_chain(chain):
                max_length = length
                new_chain = chain
                replaced = True
        except Exception:
            continue

    if replaced:
        bc.chain = new_chain

    return jsonify({
        "replaced": replaced,
        "chain_length": len(bc.chain),
        "chain": [b.__dict__ for b in bc.chain],
    })

@app.get("/debug/tamper")
def tamper():
    if len(bc.chain) < 2:
        return jsonify({"error": "need at least 2 blocks"}), 400
    bc.chain[1].transactions.append({"sender":"evil","recipient":"x","amount":999})
    return jsonify({"chain_valid": bc.valid_chain()}), 200

import sys

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(port=port, debug=True)

