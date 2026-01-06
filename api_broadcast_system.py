import os, requests, time, sys
from bitcoinlib.keys import Key

# Configurações
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 20))

def check_key(priv_key):
    try:
        priv_key = priv_key.strip()
        if not priv_key: return
        
        # Suporte a Deep Scan (xprv)
        if priv_key.startswith('xprv'):
            master = Key(priv_key)
            for i in range(20): # Amostra inicial de 20 endereços
                check_key(master.subkey_for_path(f"0/{i}").wif())
            return

        k = Key(priv_key, network='bitcoin')
        # Testa os 3 formatos principais
        formats = {
            'Legacy (1...)': None,
            'SegWit P2SH (3...)': 'p2sh-p2wpkh',
            'Native SegWit (bc1...)': 'p2wpkh'
        }

        for label, w_type in formats.items():
            addr = k.address(witness_type=w_type)
            
            # --- O PONTO CHAVE: PRINT COM FLUSH ---
            # Isso faz o endereço aparecer no GitHub Actions na hora
            print(f"🔎 W{WORKER_ID} | {label} | {addr}", flush=True)
            
            try:
                # Consulta à API
                r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    stats = data.get('chain_stats', {})
                    mempool = data.get('mempool_stats', {})
                    
                    bal = (stats.get('funded_txo_sum', 0) + mempool.get('funded_txo_sum', 0)) - \
                          (stats.get('spent_txo_sum', 0) + mempool.get('spent_txo_sum', 0))
                    
                    if bal > 0:
                        print(f"\n🚨 [SALDO ENCONTRADO] 🚨", flush=True)
                        print(f"💰 Endereço: {addr} | Saldo: {bal} sats", flush=True)
                        print(f"🔑 Chave Privada: {priv_key}", flush=True)
                        # O run_worker.sh capturará esta tag para broadcast
                        print(f"HEX_GEN:{priv_key}", flush=True) 
                
                elif r.status_code == 429:
                    print(f"⚠️ Rate Limit (Worker {WORKER_ID}). Aguardando 10s...", flush=True)
                    time.sleep(10)
            except Exception:
                pass
            
            # Delay para respeitar a API pública
            time.sleep(0.3)

    except Exception as e:
        pass

if __name__ == "__main__":
    if os.path.exists('MASTER_POOL.txt'):
        with open('MASTER_POOL.txt', 'r') as f:
            all_keys = [line.strip() for line in f if line.strip()]
        
        my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
        
        print(f"🚀 ENGINE INICIADA | Worker {WORKER_ID} | Lote: {len(my_keys)} chaves", flush=True)
        print("-" * 50, flush=True)
        
        for key in my_keys:
            check_key(key)
    else:
        print("❌ Erro: MASTER_POOL.txt não encontrado!", flush=True)
