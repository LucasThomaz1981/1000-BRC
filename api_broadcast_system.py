import json
import base64
import hashlib
import re
import os
import requests
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
PASSWORD = "Benjamin2020*1981$"
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
# Busca todos os arquivos .wallet e .txt no diretório atual
FILES_TO_SCAN = [f for f in os.listdir('.') if f.endswith(('.wallet', '.txt', '.key', '.rtf'))]

def decrypt_electrum(encrypted_data, password):
    try:
        data = base64.b64decode(encrypted_data)
        iv = data[:16]
        ct = data[16:]
        # Electrum usa double sha256 da senha como chave AES
        key = hashlib.sha256(hashlib.sha256(password.encode()).digest()).digest()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        pt = decryptor.update(ct) + decryptor.finalize()
        return pt[:-pt[-1]].decode('utf-8') # Unpadding PKCS7
    except:
        return None

def check_balance_and_send(wif, original_addr=None):
    try:
        k = Key(wif, network='bitcoin')
        # Testar formatos: Legacy, Segwit P2SH, Native Segwit
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            # Se o script já sabe o endereço alvo, foca nele, senão testa o gerado
            test_addr = original_addr if original_addr else addr
            
            r = requests.get(f"https://mempool.space/api/address/{test_addr}", timeout=10)
            if r.status_code == 200:
                stats = r.json().get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 0:
                    print(f"💰 SALDO DETECTADO: {test_addr} | {bal} sats")
                    # Lógica de criação de transação e broadcast...
                    create_tx_and_broadcast(test_addr, k.wif(), bal)
                    return True
    except:
        pass
    return False

def process_file(file_path):
    print(f"🔍 Analisando: {file_path}")
    
    # TENTATIVA 1: Tratar como Electrum Wallet (JSON + Senha)
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            if '"keystore"' in content or '"keypairs"' in content:
                data = json.loads(content)
                # Caso 1: Carteira com xprv (Master Key)
                if 'keystore' in data and 'xprv' in data['keystore']:
                    decrypted_xprv = decrypt_electrum(data['keystore']['xprv'], PASSWORD)
                    if decrypted_xprv:
                        print(f"  🔑 Master Key (xprv) descriptografada!")
                        # Aqui você pode derivar chaves ou testar a xprv diretamente
                        check_balance_and_send(decrypted_xprv)

                # Caso 2: Carteira com Importação Direta (keypairs)
                if 'keypairs' in data:
                    print(f"  🔑 Extraindo par de chaves importadas...")
                    for pub, enc_priv in data['keypairs'].items():
                        decrypted_wif = decrypt_electrum(enc_priv, PASSWORD)
                        if decrypted_wif:
                            check_balance_and_send(decrypted_wif)
    except:
        pass

    # TENTATIVA 2: Varredura de Texto (HEX/WIF/Brain) - Mantém o que funcionava antes
    try:
        with open(file_path, 'r', errors='ignore') as f:
            lines = f.readlines()
            for line in lines:
                # Busca WIFs soltos (mesmo que o arquivo não seja JSON)
                wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', line)
                for w in wifs:
                    check_balance_and_send(w)
                
                # Busca endereços e faz scan de proximidade
                addrs = re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59}', line)
                if addrs:
                    # Se achar endereço com saldo, tenta a linha atual como senha
                    for a in addrs:
                        # (Lógica de proximidade simplificada aqui)
                        pass
    except:
        pass

def create_tx_and_broadcast(addr, wif, val):
    # Insira aqui sua função de broadcast anterior para gerar o HEX_GEN
    print(f"📦 Gerando Transação para {addr}...")
    # ...

if __name__ == "__main__":
    for f in FILES_TO_SCAN:
        process_file(f)
