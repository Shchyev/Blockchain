import json
from syv_blockchain import SYV_Blockchain, SYV_PROOF_SUFFIX

syv_bc = SYV_Blockchain()

print("=== Блок генезису ===")
print(json.dumps(syv_bc.syv_chain[0], indent=2, ensure_ascii=False))
print("hash(genesis) =", SYV_Blockchain.syv_hash(syv_bc.syv_chain[0]))
print()

for syv_i in range(3):
    syv_last = syv_bc.syv_last_block
    syv_last_proof = syv_last['proof']
    syv_proof = syv_bc.syv_proof_of_work(syv_last_proof)
    syv_h = SYV_Blockchain.syv_proof_hash(syv_last_proof, syv_proof)
    syv_bc.syv_new_transaction("Shchuryk", f"recipient-{syv_i + 1}", syv_i + 1)
    syv_block = syv_bc.syv_new_block(syv_proof, SYV_Blockchain.syv_hash(syv_last))
    print(f"=== Майнінг блоку #{syv_block['index']} ===")
    print(f"last_proof = {syv_last_proof}, знайдено proof = {syv_proof}")
    print(f"Хеш PoW('{syv_last_proof}{syv_proof}') = {syv_h}")
    print(f"hash(блоку #{syv_block['index']}) = {SYV_Blockchain.syv_hash(syv_block)}")
    print(f"Хеш закінчується на '{SYV_PROOF_SUFFIX}':", syv_h.endswith(SYV_PROOF_SUFFIX))
    print(f"previous_hash = {syv_block['previous_hash']}")
    print()

print("=== Перевірка зв'язності ланцюга ===")
for syv_prev, syv_cur in zip(syv_bc.syv_chain, syv_bc.syv_chain[1:]):
    syv_ok_hash = syv_cur['previous_hash'] == SYV_Blockchain.syv_hash(syv_prev)
    syv_ok_pow = SYV_Blockchain.syv_valid_proof(syv_prev['proof'], syv_cur['proof'])
    print(f"Блок {syv_prev['index']} -> {syv_cur['index']}: "
          f"previous_hash OK={syv_ok_hash}, PoW OK={syv_ok_pow}")
print("Довжина ланцюга:", len(syv_bc.syv_chain))
