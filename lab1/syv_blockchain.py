import hashlib
import json
from time import time

SYV_SURNAME = "Shchuryk"       # прізвище (латиницею) для генезис-блоку
SYV_GENESIS_NONCE = 10112001   # [деньмісяцьрік народження]
SYV_PROOF_SUFFIX = "11"        # [місяць народження] - кінець хешу


class SYV_Blockchain(object):
    def __init__(self):
        self.syv_chain = []
        self.syv_current_transactions = []
        # Створення блоку генезису
        self.syv_new_block(syv_proof=SYV_GENESIS_NONCE,
                           syv_previous_hash=SYV_SURNAME)

    def syv_new_block(self, syv_proof, syv_previous_hash=None):
        """
        Додавання нового блоку в чейн
        :param syv_proof: <int> доказ (nonce), отриманий алгоритмом PoW
        :param syv_previous_hash: <str> хеш попереднього блоку
        :return: <dict> новий блок
        """
        syv_block = {
            'index': len(self.syv_chain) + 1,
            'timestamp': time(),
            'transactions': self.syv_current_transactions,
            'proof': syv_proof,
            'previous_hash': syv_previous_hash or self.syv_hash(self.syv_chain[-1]),
        }
        # Перезавантаження поточного списку транзакцій
        self.syv_current_transactions = []
        self.syv_chain.append(syv_block)
        return syv_block

    def syv_new_transaction(self, syv_sender, syv_recipient, syv_amount):
        """
        Додавання нової транзакції до наступного блоку
        :return: <int> індекс блоку, який буде містити транзакцію
        """
        self.syv_current_transactions.append({
            'sender': syv_sender,
            'recipient': syv_recipient,
            'amount': syv_amount,
        })
        return self.syv_last_block['index'] + 1

    @property
    def syv_last_block(self):
        return self.syv_chain[-1]

    @staticmethod
    def syv_hash(syv_block):
        """
        Обрахунок хешу SHA-256 блоку
        :param syv_block: <dict> блок
        :return: <str> хеш у hex-форматі
        """
        # Словник впорядковується за ключами, інакше хеші будуть різними
        syv_block_string = json.dumps(syv_block, sort_keys=True).encode()
        return hashlib.sha256(syv_block_string).hexdigest()

    def syv_proof_of_work(self, syv_last_proof):
        """
        Алгоритм PoW: шукаємо число p' таке, що hash(p p')
        закінчується на SYV_PROOF_SUFFIX ("11").
        """
        syv_proof = 0
        while self.syv_valid_proof(syv_last_proof, syv_proof) is False:
            syv_proof += 1
        return syv_proof

    @staticmethod
    def syv_proof_hash(syv_last_proof, syv_proof):
        syv_guess = f'{syv_last_proof}{syv_proof}'.encode()
        return hashlib.sha256(syv_guess).hexdigest()

    @staticmethod
    def syv_valid_proof(syv_last_proof, syv_proof):
        """
        Перевірка доказу: чи закінчується hash(last_proof, proof) на "11"
        """
        return SYV_Blockchain.syv_proof_hash(
            syv_last_proof, syv_proof).endswith(SYV_PROOF_SUFFIX)
