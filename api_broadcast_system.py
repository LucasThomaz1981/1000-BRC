import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
TARGET_ADDRESS = "1HYfivTqoSzjqy6eawyitWoK8HvigtU3yb"
PASSWORD = "Benjamin2020*1981$"
DEST_ADDRESS = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'

def scan_optimized():
    all_keys = []
    
    # 1. Extração de Arquivos (Mesma lógica)
    files = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                all_keys.extend(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
                all_keys.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
        except: continue

    # 2. Derivação HD (Foco em Performance)
    try:
        mnemonic = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        master = HDKey.from_passphrase(mnemonic, salt=PASSWORD, network='bitcoin')
        
        # Geramos as chaves primeiro
        for i in range(500): # Aumentado para 500 já que é rápido
            for path in [f"m/44'/0'/0'/0/{i}", f"m/49'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                all_keys.append(master.subkey_for_path(path).wif())
    except Exception as e:
        print(f"Erro derivação: {e}")

    all_keys = list(set(all_keys))
    print(f"Varrendo {len(all_keys)} chaves localmente...")

    # 3. Loop de Verificação Ultrarápido
    for wif in all_keys:
        try:
            for is_compressed in [True, False]:
                k = Key(wif, network='bitcoin', compressed=is_compressed)
                
                # TESTE LOCAL (Não gasta internet/tempo)
                addr = k.address()
                
                if addr == TARGET_ADDRESS:
                    print(f"\n!!! ALVO ENCONTRADO: {addr} !!!")
                    print(f"WIF: {wif}")
                    
                    # SÓ AGORA consultamos a API para pegar o UTXO e transmitir
                    check_and_broadcast(addr, wif)
                    return # Para após encontrar
                    
        except: continue

def check_and_broadcast(addr, wif):
    print(f"Consultando saldo para {addr}...")
    r = requests.get(f"https://mempool.space/api/address/{addr}/utxo")
    if r.status_code == 200 and r.json():
        utxos = r.json()
        utxo = max(utxos, key=lambda x: x['value'])
        amount = utxo['value'] - 5000 # Taxa de minerador (ajustável)
        
        tx = Transaction(network='bitcoin')
        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
        tx.add_output(value=amount, address=DEST_ADDRESS)
        tx.sign([wif])
        
        hex_tx = tx.raw_hex()
        print(f"HEX_GEN:{hex_tx}")
