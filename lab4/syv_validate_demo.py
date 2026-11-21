import copy

from syv_blockchain_app import SYV_Blockchain

syv_bc = SYV_Blockchain()
for syv_i in range(3):
    syv_last = syv_bc.syv_last_block
    syv_bc.syv_new_transaction("0", "miner", 10)
    syv_bc.syv_new_block(syv_bc.syv_proof_of_work(syv_last['proof']),
                         SYV_Blockchain.syv_hash(syv_last))

print("1) Оригінальний ланцюг, довжина", len(syv_bc.syv_chain))
print("   syv_valid_chain ->", syv_bc.syv_valid_chain(syv_bc.syv_chain, True))

syv_fake = copy.deepcopy(syv_bc.syv_chain)
syv_fake[2]['transactions'][0]['amount'] = 1000
print("2) Змінено суму транзакції в блоці 3 (10 -> 1000)")
print("   syv_valid_chain ->", syv_bc.syv_valid_chain(syv_fake, True))

syv_fake = copy.deepcopy(syv_bc.syv_chain)
syv_fake[1]['proof'] += 1
print("3) Змінено proof блоку 2")
print("   syv_valid_chain ->", syv_bc.syv_valid_chain(syv_fake, True))

syv_fake = copy.deepcopy(syv_bc.syv_chain)
syv_fake[3]['previous_hash'] = '0' * 64
print("4) Підмінено previous_hash блоку 4")
print("   syv_valid_chain ->", syv_bc.syv_valid_chain(syv_fake, True))
