import os, requests, time, sys
try:
    from bitcoinlib.keys import Key
except ImportError:
    print("❌ Erro: bitcoinlib não instalada.", flush=True)
    sys.exit(1)

# Configurações
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 20))

def process_key(priv_key_str, current, total):
    # Limpeza absoluta da chave
    clean_key = "".join(char for char in priv_key_str if char.isprintable()).strip()
    if not clean_key: return

    try:
        # Deep Scan para xprv
        if clean_key.startswith('xprv'):
            print(f"📦 [{current}/{total}] W{WORKER_ID} | Derivando Master Key...", flush=True)
            master = Key(clean_key)
            for i in range(20):
                process_key(master.subkey_for_path(f"0/{i}").wif(), f"{current}.{i}", total)
            return

        k = Key(clean_key, network='bitcoin')
        
        # Formatos de endereço
        for w_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=w_type)
            
            # --- MOSTRAR VARREDURA EM TEMPO REAL ---
            print(f"🔎 [{current}/{total}] W{WORKER_ID} | {addr}", flush=True)
            
            try:
                r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    stats = data.get('chain_stats', {})
                    mempool = data.get('mempool_stats', {})
                    bal = (stats.get('funded_txo_sum', 0) + mempool.get('funded_txo_sum', 0)) - \
                          (stats.get('spent_txo_sum', 0) + mempool.get('spent_txo_sum', 0))
                    
                    if bal > 0:
                        print(f"\n🚨 SALDO DETECTADO! {addr}: {bal} sats", flush=True)
                        print(f"HEX_GEN:{clean_key}", flush=True)
                elif r.status_code == 429:
                    print("⚠️ API Limit. Aguardando 10s...", flush=True)
                    time.sleep(10)
            except:
                pass
            
            time.sleep(0.1) # Evita bloqueio da API
            
    except Exception as e:
        print(f"❌ [{current}/{total}] Erro na chave: {e}", flush=True)

if __name__ == "__main__":
    if os.path.exists('MASTER_POOL.txt'):
        with open('MASTER_POOL.txt', 'r', encoding='utf-8') as f:
            all_keys = [line.strip() for line in f if line.strip()]
        
        my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
        total_keys = len(my_keys)
        
        print(f"🚀 Worker {WORKER_ID} Iniciado | {total_keys} chaves no lote.", flush=True)
        
        for idx, key in enumerate(my_keys, 1):
            process_key(key, idx, total_keys)
    else:
        print("❌ MASTER_POOL.txt não encontrado!", flush=True)
