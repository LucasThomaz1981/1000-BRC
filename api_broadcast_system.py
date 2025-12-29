import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

# --- PARÂMETROS EXTRAÍDOS DO PROTOCOLO ---
TARGET_ADDRESS = "1HYfivTqoSzjqy6eawyitWoK8HvigtU3yb"
PASSWORD = "Benjamin2020*1981$"
MESSAGE = "BITCOIN IS AMAZING AND SATOSHI IS GENIUS"

def extract_keys(filename):
    keys = []
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Busca WIF e Hexadecimal de 64 caracteres
        keys.extend(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
        keys.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
    except: pass
    return keys

def scan_final_synchronized():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys = []
    
    # 1. Fontes de Arquivo (Incluindo chavprivelet1.txt)
    files = [
        'privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt',
        'chaves_extraidas_e_enderecos_1.txt', 'combined_recovered_keys.txt'
    ]
    
    for f in files:
        found = extract_keys(f)
        if found:
            print(f"Sucesso: {len(found)} chaves extraídas de {f}")
            all_keys.extend(found)

    # 2. Derivação Baseada na Senha Benjamin (BIP39 + Passphrase)
    try:
        mnemonic = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        # O protocolo usa a senha como Passphrase para gerar uma nova carteira
        master = HDKey.from_passphrase(mnemonic, passphrase=PASSWORD, network='bitcoin')
        print(f"Derivando endereços com Passphrase: {PASSWORD}")
        for i in range(200): # Aumentado para cobrir maior raio
            for path in [f"m/44'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                all_keys.append(master.subkey_for_path(path).wif())
    except Exception as e:
        print(f"Aviso na derivação HD: {e}")

    all_keys = list(set(all_keys))
    print(f"Varredura Sincronizada: {len(all_keys)} chaves totais.")

    # 3. Varredura de UTXO com foco no Alvo
    for wif in all_keys:
        try:
            # Testamos Comprimido e Não-Comprimido para garantir o alvo 1HYf...
            for compressed in [True, False]:
                k = Key(wif, network='bitcoin', compressed=compressed)
                for t_type in ['p2pkh', 'p2wpkh']:
                    addr = k.address(witness_type=t_type)
                    
                    # Verificação instantânea do alvo do relatório
                    if addr == TARGET_ADDRESS:
                        print(f"!!! ALVO LOCALIZADO: {addr} !!!")

                    r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=5)
                    if r.status_code == 200 and r.json():
                        utxos = r.json()
                        print(f"!!! SALDO ENCONTRADO EM {addr} !!!")
                        utxo = max(utxos, key=lambda x: x['value'])
                        amount = utxo['value'] - 80000 # Taxa de ultra-prioridade
                        
                        tx = Transaction(network='bitcoin')
                        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                        tx.add_output(value=amount, address=dest_address)
                        tx.sign([wif])
                        print(f"HEX_GEN:{tx.raw_hex()}")
            time.sleep(0.01)
        except: continue

if __name__ == "__main__":
    scan_final_synchronized()
