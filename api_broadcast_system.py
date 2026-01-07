import os, requests, time, sys
try:
    from bitcoinlib.keys import Key
except ImportError:
    print("❌ Erro: bitcoinlib não instalada.", flush=True)
    sys.exit(1)

DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 20))

# Lista de APIs para evitar bloqueios
APIS = [
    "https://mempool.space/api/address/{}",
    "https://blockstream.info/api/address/{}",
    "https://blockchain.info/rawaddr/{}" # Nota: Formato de resposta diferente, tratado abaixo
]

def get_balance(addr):
    """Tenta obter o saldo em múltiplas APIs em caso de erro."""
    for api_url in APIS:
        try:
            url = api_url.format(addr)
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                # Tratamento para Mempool/Blockstream
                if 'chain_stats' in data:
                    sats = (data['chain_stats']['funded_txo_sum'] + data['mempool_stats']['funded_txo_sum']) - \
                           (data['chain_stats']['spent_txo_sum'] + data['mempool_stats']['spent_txo_sum'])
                    return sats
                # Tratamento para Blockchain.info
                elif 'final_balance' in data:
                    return data['final_balance']
            elif r.status_code == 429: # Too Many Requests
                continue 
        except:
            continue
    return None

def process_key(priv_key_str, current, total):
    clean_key = "".join(char for char in priv_key_str if char.isprintable()).strip()
    if not clean_key: return

    try:
        k = Key(clean_key, network='bitcoin')
        addr_configs = [
            ('Legacy', 'base58', 'p2pkh'),
            ('P2SH', 'base58', 'p2sh_p2wpkh'),
            ('SegWit', 'bech32', 'p2wpkh')
        ]

        for label, enc, script in addr_configs:
            addr = k.address(encoding=enc, script_type=script)
            sats = get_balance(addr)
            
            if sats is not None:
                bal_btc = sats / 100000000.0
                status = "✅" if sats == 0 else "🚨 SALDO!"
                print(f"🔎 [{current}/{total}] W{WORKER_ID} | {status} | {label:6} | {addr} | Bal: {bal_btc:.8f} BTC", flush=True)
                
                if sats > 0:
                    print(f"HEX_GEN:{clean_key}", flush=True)
            else:
                print(f"⚠️ [{current}/{total}] W{WORKER_ID} | SKIPPED (API Offline) | {addr}", flush=True)
            
            # Delay aumentado para 0.5s para evitar o "Operation Canceled" por excesso de tráfego
            time.sleep(0.5)

    except Exception as e:
        pass

if __name__ == "__main__":
    if os.path.exists('MASTER_POOL.txt'):
        with open('MASTER_POOL.txt', 'r', encoding='utf-8', errors='ignore') as f:
            all_keys = [line.strip() for line in f if line.strip()]
        
        my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
        total_keys = len(my_keys)
        
        print(f"🚀 Worker {WORKER_ID} Iniciado | {total_keys} chaves.", flush=True)
        for idx, key in enumerate(my_keys, 1):
            process_key(key, idx, total_keys)
