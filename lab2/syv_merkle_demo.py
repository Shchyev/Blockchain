"""ЛР2. Демонстрація побудови дерева Меркла для транзакцій мемпулу."""
from syv_blockchain_app import (SYV_Blockchain, syv_merkle_root, syv_sha256,
                                syv_tx_hash)

syv_bc = SYV_Blockchain()
syv_bc.syv_new_transaction("Shchuryk", "Alice", 3)
syv_bc.syv_new_transaction("Alice", "Bob", 2)
syv_bc.syv_new_transaction("Bob", "Shchuryk", 1)
syv_bc.syv_new_transaction("0", "miner", 1)   # винагорода майнеру

print("Мемпул:", len(syv_bc.syv_mempool), "транзакції")
syv_level = [syv_tx_hash(t) for t in syv_bc.syv_mempool]
syv_depth = 0
print(f"Рівень {syv_depth} (листя):")
for syv_h in syv_level:
    print("   ", syv_h)
while len(syv_level) > 1:
    if len(syv_level) % 2:
        syv_level.append(syv_level[-1])
    syv_level = [syv_sha256(syv_level[i] + syv_level[i + 1])
                 for i in range(0, len(syv_level), 2)]
    syv_depth += 1
    print(f"Рівень {syv_depth}:")
    for syv_h in syv_level:
        print("   ", syv_h)

syv_root = syv_merkle_root(syv_bc.syv_mempool)
print("\nКорінь Меркла (syv_merkle_root):", syv_root)

syv_last = syv_bc.syv_last_block
syv_proof = syv_bc.syv_proof_of_work(syv_last['proof'])
syv_block = syv_bc.syv_new_block(syv_proof, SYV_Blockchain.syv_hash(syv_last))
print("Блок #%d намайнено, proof=%d" % (syv_block['index'], syv_proof))
print("merkle_root у блоці:", syv_block['merkle_root'])
print("Збігається з обчисленим:", syv_block['merkle_root'] == syv_root)
print("Мемпул після майнінгу:", syv_bc.syv_mempool)
