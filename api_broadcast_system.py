import os, requests, time, sys
try:
    from bitcoinlib.keys import Key
except ImportError:
    print("❌ Erro: bitcoinlib não instalada.", flush=True)
    sys.exit(1)

WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 20))
CP_FILE = f"checkpoints/worker_{WORKER_ID}.txt"

def get_last_pos():
    if os.path.exists(CP_FILE):
        with open(CP_FILE, 'r') as f:
            return int(f.read().strip())
    return 0

def check_addr(addr):
    # Fallback entre Mempool e Blockstream para evitar cancelamento por erro 429
    apis = [f"https://mempool.space/api/address/{addr}", f"https://blockstream.info/api/address/{addr}"]
    for api in apis:
        try:
            r = requests.get(api, timeout=10)
            if r.status_code == 200:
                d = r.json()
                s = d.get('chain_stats', {})
                m = d.get('mempool_stats', {})
                return (s.get('funded_txo_sum', 0) + m.get('funded_txo_sum', 0)) - \
                       (s.get('spent_txo_sum', 0) + m.get('spent_txo_sum', 0))
            if r.status_code == 429:
                time.sleep(10) # API saturada, aguarda
        except: continue
    return None

if __name__ == "__main__":
    os.makedirs('checkpoints', exist_ok=True)
    with open('MASTER_POOL.txt', 'r') as f:
        keys = [l.strip() for l in f if l.strip()]
    
    my_keys = [keys[i] for i in range(len(keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    start_idx = get_last_pos()
    
    print(f"🚀 Worker {WORKER_ID} retomando da chave {start_idx + 1}/{len(my_keys)}", flush=True)

    for i in range(start_idx, len(my_keys)):
        k_hex = my_keys[i]
        # Testa Comprimida (C) e Não-Comprimida (U)
        for comp in [True, False]:
            key_obj = Key(k_hex, network='bitcoin', compressed=comp)
            # Legacy, P2SH, SegWit
            for lbl, enc, scr in [('Legacy', 'base58', 'p2pkh'), ('P2SH', 'base58', 'p2sh_p2wpkh'), ('SegWit', 'bech32', 'p2wpkh')]:
                if not comp and enc == 'bech32': continue
                addr = key_obj.address(encoding=enc, script_type=scr)
                sats = check_addr(addr)
                
                if sats is not None:
                    print(f"🔎 [{i+1}/{len(my_keys)}] W{WORKER_ID} | {'✅' if sats==0 else '🚨'} | {lbl:6} | {addr} | {sats/1e8:.8f} BTC", flush=True)
                    if sats > 0: print(f"HEX_GEN:{k_hex}", flush=True)
                
                time.sleep(0.5) # Aumentado para evitar o cancelamento por excesso de tráfego
        
        # Grava o checkpoint a cada chave processada
        with open(CP_FILE, 'w') as f: f.write(str(i + 1))
