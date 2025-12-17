from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import List, Dict, Any


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Block:
    index: int
    timestamp: str
    transactions: List[Dict[str, Any]]
    proof: int
    previous_hash: str

    def to_ordered_json(self) -> str:
        # Deterministic hash için sıralı JSON
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


class Blockchain:
    def __init__(self, difficulty_prefix: str = "0000"):
        self.difficulty_prefix = difficulty_prefix
        self.chain: List[Block] = []
        self.current_transactions: List[Dict[str, Any]] = []

        # Genesis block
        self.new_block(proof=0, previous_hash="0")

    def new_transaction(self, sender: str, recipient: str, amount: float) -> int:
        self.current_transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
        })
        return self.last_block.index + 1

    def new_block(self, proof: int, previous_hash: str | None = None) -> Block:
        block = Block(
            index=len(self.chain) + 1,
            timestamp=utc_now_iso(),
            transactions=self.current_transactions,
            proof=proof,
            previous_hash=previous_hash or self.hash(self.last_block),
        )
        self.current_transactions = []
        self.chain.append(block)
        return block

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def hash(self, block: Block) -> str:
        return sha256(block.to_ordered_json())

    def proof_of_work(self, last_proof: int, last_hash: str, transactions: list[dict]) -> int:
        proof = 0
        while not self.valid_proof(last_proof, proof, last_hash, transactions):
            proof += 1
        return proof


    def valid_proof(self, last_proof: int, proof: int, last_hash: str, transactions: list[dict]) -> bool:
        tx_str = json.dumps(transactions, sort_keys=True, separators=(",", ":"))
        guess = f"{last_proof}{last_hash}{tx_str}{proof}"
        guess_hash = sha256(guess)
        return guess_hash.startswith(self.difficulty_prefix)

    
    def valid_chain(self, chain: List[Block] | None = None) -> bool:
        chain = chain or self.chain
        for i in range(1, len(chain)):
            prev = chain[i - 1]
            curr = chain[i]

            # 1) previous_hash doğru mu?
            if curr.previous_hash != self.hash(prev):
                return False

            # 2) PoW doğru mu? (prev proof + curr proof + prev hash)
            prev_hash = self.hash(prev)
            if not self.valid_proof(prev.proof, curr.proof, prev_hash, curr.transactions):
                return False

        return True



if __name__ == "__main__":
    bc = Blockchain(difficulty_prefix="0000")

    bc.new_transaction("alice", "bob", 10)
    bc.new_transaction("bob", "charlie", 2.5)

    last = bc.last_block
    last_hash = bc.hash(last)
    proof = bc.proof_of_work(last.proof, last_hash, bc.current_transactions)
    mined = bc.new_block(proof=proof, previous_hash=last_hash)

    print("Mined block:", asdict(mined))
    print("Chain length:", len(bc.chain))
    print("Last block hash:", bc.hash(bc.last_block))
    print("Chain valid?", bc.valid_chain())

    # Zinciri bozma testi (tamper)
    bc.chain[1].transactions[0]["amount"] = 999
    print("Chain valid after tamper?", bc.valid_chain())

