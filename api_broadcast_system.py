import requests
import re
import time
from bitcoinlib.keys import Key
from bitcoinlib.mnemonic import Mnemonic
from bitcoinlib.transactions import Transaction

def scan_full_protocol():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys = []

    # 1. Extrair WIFs do arquivo
    try:
        with open('privatekeys.txt', 'r') as f:
            content = f.read()
        wif_keys = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        all_keys.extend(list(set(wif_keys)))
    except:
        print("Erro ao ler privatekeys.txt")

    # 2. Derivar chaves da Mnemónica (Frase de 12 palavras)
    try:
        phrase = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        print(f"Derivando endereços da mnemónica...")
        for i in range(100): # Testa os primeiros 100 índices de derivação
            # Derivação padrão BIP44, BIP49 e BIP84
            for path in [f"m/44'/0'/0'/0/{i}", f"m/49'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                k = Key(phrase, network='bitcoin', path=path)
                all_keys.append(k.wif())
    except Exception as e:
        print(f"Erro na derivação: {e}")

    print(f"Total de chaves para testar: {len(all_keys)}")

    # 3. Varredura de Rede
    for wif in all_keys:
        try:
            k = Key(wif, network='bitcoin')
            # Testamos os 3 tipos de endereço para cada chave
            for t_type in ['p2pkh', 'p2wpkh', 'p2sh-p2wpkh']:
                addr = k.address(witness_type=t_type)
                url = f"https://mempool.space/api/address/{addr}/utxo"
                
                r = requests.get(url, timeout=10)
                if r.status_code == 429:
                    time.sleep(2)
                    continue
                utxos = r.json()

                if utxos:
                    print(f"!!! SUCESSO !!! Endereço: {addr} ({t_type})")
                    utxo = max(utxos, key=lambda x: x['value'])
                    fee = 15000 
                    amount = utxo['value'] - fee

                    if amount > 1000:
                        tx = Transaction(network='bitcoin')
                        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                        tx.add_output(value=amount, address=dest_address)
                        tx.sign([wif])
                        print(f"HEX_GEN:{tx.raw_hex()}")
            
            time.sleep(0.2)
        except:
            continue

if __name__ == "__main__":
    scan_full_protocol()
