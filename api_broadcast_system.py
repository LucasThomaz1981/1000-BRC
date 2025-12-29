import requests
import time
import re
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
TARGET_ADDRESS = "1HYfivTqoSzjqy6eawyitWoK8HvigtU3yb"
PASSWORD = "Benjamin2020*1981$"
MNEMONIC = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
DEST_ADDRESS = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'

def check_balance(address):
    """Consulta saldo via API do Mempool.space"""
    try:
        r = requests.get(f"https://mempool.space/api/address/{address}/utxo", timeout=5)
        if r.status_code == 200:
            utxos = r.json()
            if utxos:
                return sum(u['value'] for u in utxos), utxos
    except:
        pass
    return 0, []

def create_broadcast_hex(addr, wif, utxos):
    """Gera o HEX da transação para ser capturado pelo script shell"""
    try:
        total_in = sum(u['value'] for u in utxos)
        fee = 5000  # Taxa fixa em satoshis
        amount = total_in - fee
        
        if amount <= 0: return
        
        tx = Transaction(network='bitcoin')
        for u in utxos:
            tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
        
        tx.add_output(value=amount, address=DEST_ADDRESS)
        tx.sign([wif])
        print(f"HEX_GEN:{tx.raw_hex()}")
    except Exception as e:
        print(f"Erro ao gerar HEX: {e}")

def run_complete_scan():
    try:
        # Correção final: Passando mnemonic e password como argumentos posicionais
        master = HDKey.from_passphrase(MNEMONIC, PASSWORD, network='bitcoin')
        print(f"✅ Master Key gerada com sucesso.")
        print(f"🔎 Iniciando varredura profunda (Legacy, SegWit, Native SegWit)...")

        # Diferentes caminhos: 44' (Legacy), 49' (SegWit), 84' (Native SegWit)
        purposes = [44, 49, 84]
        
        for purpose in purposes:
            for account in range(2): # Contas 0 e 1
                for change in [0, 1]: # Recebimento e Troco
                    print(f"\nScaneando m/{purpose}'/0'/{account}'/{change}/...")
                    
                    for i in range(150): # Índices de 0 a 149
                        path = f"m/{purpose}'/0'/{account}'/{change}/{i}"
                        derived = master.subkey_for_path(path)
                        wif = derived.wif()
                        
                        # Testar endereços comprimidos e não comprimidos
                        for comp in [True, False]:
                            k = Key(wif, network='bitcoin', compressed=comp)
                            
                            # Ajusta o tipo de endereço conforme o 'purpose'
                            if purpose == 44: addr = k.address() # 1...
                            elif purpose == 49: addr = k.address(witness_type='p2sh-p2wpkh') # 3...
                            elif purpose == 84: addr = k.address(witness_type='p2wpkh') # bc1...
                            
                            # 1. Checagem do Alvo Específico
                            if addr == TARGET_ADDRESS:
                                print(f"⭐ !!! ALVO ENCONTRADO NO CAMINHO {path} !!!")
                            
                            # 2. Checagem de Saldo Geral
                            balance, utxos = check_balance(addr)
                            if balance > 0:
                                print(f"💰 SALDO DETECTADO: {addr} | Valor: {balance} sats")
                                print(f"Path: {path} | WIF: {wif}")
                                create_broadcast_hex(addr, wif, utxos)
                                
                        # Delay para evitar Rate Limit da API
                        time.sleep(0.1)
                        if i % 50 == 0 and i > 0:
                            print(f"  Índice {i} atingido...")

        print("\n--- Varredura finalizada ---")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")

if __name__ == "__main__":
    run_complete_scan()

