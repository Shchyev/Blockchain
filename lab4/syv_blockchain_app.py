import argparse
import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
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
        self.syv_nodes = set()     # сусідні вузли мережі
        self.syv_new_block(syv_proof=SYV_GENESIS_NONCE,
                           syv_previous_hash=SYV_SURNAME)
        # Генезис однаковий на всіх вузлах (фіксована мітка часу),
        # інакше ланцюги різних вузлів не мали б спільного початку
        self.syv_chain[0]['timestamp'] = 1005343200.0  # 10.11.2001

    def syv_register_node(self, syv_address):
        """
        Додає новий вузол до списку вузлів
        :param syv_address: <str> напр. 'http://127.0.0.1:5001'
        """
        syv_parsed = urlparse(syv_address)
        syv_netloc = syv_parsed.netloc or syv_parsed.path
        if not syv_netloc:
            raise ValueError('Invalid URL')
        self.syv_nodes.add(syv_netloc)

    def syv_valid_chain(self, syv_chain, syv_verbose=False):
        """
        Перевіряє, чи є ланцюг валідним:
          1) previous_hash кожного блоку == хешу попереднього блоку;
          2) proof задовольняє критерію PoW (хеш закінчується на "11");
          3) merkle_root відповідає транзакціям блоку.
        """
        if syv_chain[0]['previous_hash'] != SYV_SURNAME:
            return False
        syv_last_block = syv_chain[0]
        for syv_block in syv_chain[1:]:
            if syv_block['previous_hash'] != self.syv_hash(syv_last_block):
                if syv_verbose:
                    print(f"Блок {syv_block['index']}: hash don't match")
                return False
            if not self.syv_valid_proof(syv_last_block['proof'], syv_block['proof']):
                if syv_verbose:
                    print(f"Блок {syv_block['index']}: proof is not valid")
                return False
            if syv_block['merkle_root'] != syv_merkle_root(syv_block['transactions']):
                if syv_verbose:
                    print(f"Блок {syv_block['index']}: merkle root mismatch")
                return False
            syv_last_block = syv_block
        return True

    def syv_resolve_conflicts(self):
        """
        Алгоритм консенсусу: замінюємо свій ланцюг найдовшим
        валідним ланцюгом серед сусідніх вузлів.
        :return: <bool> True, якщо ланцюг було замінено
        """
        syv_new_chain = None
        syv_max_length = len(self.syv_chain)
        for syv_node in self.syv_nodes:
            try:
                syv_resp = requests.get(f'http://{syv_node}/chain', timeout=5)
            except requests.RequestException:
                continue
            if syv_resp.status_code == 200:
                syv_length = syv_resp.json()['length']
                syv_chain = syv_resp.json()['chain']
                if syv_length > syv_max_length and self.syv_valid_chain(syv_chain):
                    syv_max_length = syv_length
                    syv_new_chain = syv_chain
        if syv_new_chain:
            self.syv_chain = syv_new_chain
            # транзакції, що вже потрапили в новий ланцюг, видаляються з мемпулу
            syv_in_chain = {t.get('tx_hash') for b in syv_new_chain
                            for t in b['transactions']}
            self.syv_mempool = [t for t in self.syv_mempool
                                if t['tx_hash'] not in syv_in_chain]
            return True
        return False

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


@syv_app.route('/nodes/register', methods=['POST'])
def syv_register_nodes():
    syv_values = request.get_json(silent=True) or {}
    syv_nodes = syv_values.get('nodes')
    if not syv_nodes:
        return "Error: Please supply a valid list of nodes", 400
    try:
        for syv_node in syv_nodes:
            syv_blockchain.syv_register_node(syv_node)
    except ValueError:
        return "Incorrect host address", 400
    return jsonify({
        'message': 'New nodes have been added',
        'total_nodes': sorted(syv_blockchain.syv_nodes),
    }), 201


@syv_app.route('/nodes/resolve', methods=['GET'])
def syv_consensus():
    syv_replaced = syv_blockchain.syv_resolve_conflicts()
    if syv_replaced:
        syv_response = {'message': 'Our chain was replaced',
                        'new_chain': syv_blockchain.syv_chain}
    else:
        syv_response = {'message': 'Our chain is authoritative',
                        'chain': syv_blockchain.syv_chain}
    syv_response['length'] = len(syv_blockchain.syv_chain)
    return jsonify(syv_response), 200


if __name__ == '__main__':
    syv_parser = argparse.ArgumentParser()
    syv_parser.add_argument('-p', '--port', default=5000, type=int,
                            help='port to listen on')
    syv_args = syv_parser.parse_args()
    syv_app.run(host='0.0.0.0', port=syv_args.port)
