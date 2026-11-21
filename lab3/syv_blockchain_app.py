import hashlib
import json
from time import time
from uuid import uuid4

from flask import Flask, jsonify, request

SYV_SURNAME = "Shchuryk"       # previous_hash генезис-блоку
SYV_GENESIS_NONCE = 10112001   # nonce генезис-блоку
SYV_PROOF_SUFFIX = "11"        # хеш доказу закінчується на місяць народження
SYV_MINING_REWARD = 10         # винагорода за майнінг = [день народження]


def syv_sha256(syv_data: str) -> str:
    return hashlib.sha256(syv_data.encode()).hexdigest()


def syv_tx_hash(syv_tx: dict) -> str:
    """Хеш однієї транзакції (лист дерева Меркла)."""
    return syv_sha256(json.dumps(syv_tx, sort_keys=True))


def syv_merkle_root(syv_transactions: list) -> str:
    """
    Побудова дерева Меркла: хеші транзакцій попарно об'єднуються
    і хешуються, доки не залишиться один - корінь.
    При непарній кількості останній хеш дублюється.
    """
    if not syv_transactions:
        return syv_sha256("")
    syv_level = [syv_tx_hash(t) for t in syv_transactions]
    while len(syv_level) > 1:
        if len(syv_level) % 2 == 1:
            syv_level.append(syv_level[-1])
        syv_level = [syv_sha256(syv_level[i] + syv_level[i + 1])
                     for i in range(0, len(syv_level), 2)]
    return syv_level[0]


class SYV_Blockchain(object):
    def __init__(self):
        self.syv_chain = []
        self.syv_mempool = []      # непідтверджені транзакції
        self.syv_new_block(syv_proof=SYV_GENESIS_NONCE,
                           syv_previous_hash=SYV_SURNAME)

    def syv_new_block(self, syv_proof, syv_previous_hash=None):
        """Створює блок із транзакцій мемпулу та додає його в чейн."""
        syv_txs = list(self.syv_mempool)
        syv_block = {
            'index': len(self.syv_chain) + 1,
            'timestamp': time(),
            'transactions': syv_txs,
            'merkle_root': syv_merkle_root(syv_txs),
            'proof': syv_proof,
            'previous_hash': syv_previous_hash or self.syv_hash(self.syv_chain[-1]),
        }
        self.syv_mempool = []      # мемпул очищується
        self.syv_chain.append(syv_block)
        return syv_block

    def syv_new_transaction(self, syv_sender, syv_recipient, syv_amount):
        """Додає транзакцію в мемпул; повертає індекс майбутнього блоку."""
        syv_tx = {
            'sender': syv_sender,
            'recipient': syv_recipient,
            'amount': syv_amount,
            'timestamp': time(),
        }
        syv_tx['tx_hash'] = syv_tx_hash(syv_tx)
        self.syv_mempool.append(syv_tx)
        return self.syv_last_block['index'] + 1

    def syv_balance(self, syv_address, syv_include_mempool=True):
        """
        Каса (баланс) адреси: сума вхідних мінус сума вихідних
        у підтверджених блоках; вихідні з мемпулу теж віднімаються,
        щоб не допустити подвійної витрати.
        """
        syv_total = 0
        for syv_block in self.syv_chain:
            for syv_tx in syv_block['transactions']:
                if syv_tx['recipient'] == syv_address:
                    syv_total += syv_tx['amount']
                if syv_tx['sender'] == syv_address:
                    syv_total -= syv_tx['amount']
        if syv_include_mempool:
            for syv_tx in self.syv_mempool:
                if syv_tx['sender'] == syv_address:
                    syv_total -= syv_tx['amount']
        return syv_total

    @property
    def syv_last_block(self):
        return self.syv_chain[-1]

    @staticmethod
    def syv_hash(syv_block):
        syv_block_string = json.dumps(syv_block, sort_keys=True).encode()
        return hashlib.sha256(syv_block_string).hexdigest()

    def syv_proof_of_work(self, syv_last_proof):
        syv_proof = 0
        while self.syv_valid_proof(syv_last_proof, syv_proof) is False:
            syv_proof += 1
        return syv_proof

    @staticmethod
    def syv_valid_proof(syv_last_proof, syv_proof):
        syv_guess_hash = syv_sha256(f'{syv_last_proof}{syv_proof}')
        return syv_guess_hash.endswith(SYV_PROOF_SUFFIX)


# Створення вузла
syv_app = Flask(__name__)
# Унікальна адреса вузла (гаманець майнера)
syv_node_identifier = str(uuid4()).replace('-', '')
syv_blockchain = SYV_Blockchain()


@syv_app.route('/mine', methods=['GET'])
def syv_mine():
    syv_last_block = syv_blockchain.syv_last_block
    syv_proof = syv_blockchain.syv_proof_of_work(syv_last_block['proof'])

    # Винагорода майнеру: відправник "0" - нова монета
    syv_blockchain.syv_new_transaction(
        syv_sender="0",
        syv_recipient=syv_node_identifier,
        syv_amount=SYV_MINING_REWARD,
    )
    syv_previous_hash = syv_blockchain.syv_hash(syv_last_block)
    syv_block = syv_blockchain.syv_new_block(syv_proof, syv_previous_hash)
    return jsonify({
        'message': "New Block Forged",
        'index': syv_block['index'],
        'transactions': syv_block['transactions'],
        'merkle_root': syv_block['merkle_root'],
        'proof': syv_block['proof'],
        'proof_hash': syv_sha256(f"{syv_last_block['proof']}{syv_proof}"),
        'previous_hash': syv_block['previous_hash'],
    }), 200


@syv_app.route('/transactions/new', methods=['POST'])
def syv_new_transaction():
    syv_values = request.get_json(silent=True) or {}
    syv_required = ['sender', 'recipient', 'amount']
    if not all(k in syv_values for k in syv_required):
        return 'Missing values', 400
    syv_amount = syv_values['amount']
    if not isinstance(syv_amount, (int, float)) or syv_amount <= 0:
        return jsonify({'message': 'Amount must be a positive number'}), 400
    # Перевірка відносно наявної каси відправника
    syv_available = syv_blockchain.syv_balance(syv_values['sender'])
    if syv_available < syv_amount:
        return jsonify({
            'message': 'Insufficient funds',
            'available': syv_available,
            'requested': syv_amount,
        }), 400
    syv_index = syv_blockchain.syv_new_transaction(
        syv_values['sender'], syv_values['recipient'], syv_values['amount'])
    return jsonify({'message': f'Transaction will be added to Block {syv_index}'}), 201


@syv_app.route('/mempool', methods=['GET'])
def syv_get_mempool():
    return jsonify({
        'mempool': syv_blockchain.syv_mempool,
        'size': len(syv_blockchain.syv_mempool),
        'merkle_root_preview': syv_merkle_root(syv_blockchain.syv_mempool),
    }), 200


@syv_app.route('/chain', methods=['GET'])
def syv_full_chain():
    return jsonify({
        'chain': syv_blockchain.syv_chain,
        'length': len(syv_blockchain.syv_chain),
    }), 200


@syv_app.route('/balance/<syv_address>', methods=['GET'])
def syv_get_balance(syv_address):
    return jsonify({
        'address': syv_address,
        'confirmed': syv_blockchain.syv_balance(syv_address, False),
        'available': syv_blockchain.syv_balance(syv_address, True),
    }), 200


@syv_app.route('/node/id', methods=['GET'])
def syv_node_id():
    return jsonify({'node_identifier': syv_node_identifier}), 200


if __name__ == '__main__':
    syv_app.run(host='0.0.0.0', port=5000)
