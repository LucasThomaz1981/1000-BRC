import requests
import argparse
import sys
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

def sign_and_liquidate(block_num, wif_key):
    try:
        # 1. Carregar a chave privada Benjamin
        # A bitcoinlib identifica automaticamente se é P2PKH
        key = Key(wif_key, network='bitcoin')
        source_address = key.address()
        
        # 2. Buscar UTXOs Reais (Usando a API do Mempool.space como no seu script)
        utxo_url = f"https://mempool.space/api/address/{source_address}/utxo"
        response = requests.get(utxo_url, timeout=15)
        utxos = response.json()
        
        if not utxos:
            # Se não houver saldo, retornamos vazio para o workflow não quebrar
            return ""

        # 3. Montar a transação para o endereço intermediário
        # Conforme o seu arquivo: 1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL
        dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
        
        # Seleciona o primeiro UTXO disponível
        utxo = utxos[0]
        fee = 2500  # Taxa em satoshis para confirmação rápida
        amount = utxo['value'] - fee

        tx = Transaction(network='bitcoin')
        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'])
        tx.add_output(value=amount, address=dest_address)
        
        # 4. Assinar
        tx.sign([wif_key])
        return tx.raw_hex()

    except Exception as e:
        return ""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=int)
    parser.add_argument("--passphrase", type=str)
    args = parser.parse_args()
    
    # O Workflow capturará este print para o comando curl
    print(sign_and_liquidate(args.block, args.passphrase))
