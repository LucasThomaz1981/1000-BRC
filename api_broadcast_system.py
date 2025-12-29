import requests
import time
import re
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.mnemonic import Mnemonic
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
TARGET_ADDRESS = "1HYfivTqoSzjqy6eawyitWoK8HvigtU3yb"
PASSWORD = "Benjamin2020*1981$"
MNEMONIC_11 = "tree dwarf rubber off tree finger hair hope emerge earn friend"
# ENDEREÇO DE CUSTÓDIA (COLD WALLET)
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'

def check_balance(address):
    """Consulta saldo real na rede Bitcoin via Mempool.space"""
    try:
        r = requests.get(f"https://mempool.space/api/address/{address}/utxo", timeout=3)
        if r.status_code == 200:
            utxos = r.json()
            if utxos:
                total = sum(u['value'] for u in utxos)
                return total, utxos
    except: pass
    return 0, []

def clean_rtf(filename):
    """Remove formatação RTF para extrair chaves puras"""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            clean_text = re.sub(r'\\[a-z0-9]+(?:\s|-?\d+)?', '', content)
            clean_text = re.sub(r'[{}]', '', clean_text)
            return clean_text
    except: return ""

def create_tx_hex(addr, wif, utxos):
    """Gera o HEX da transação para broadcast"""
    try:
        total_in = sum(u['value'] for u in utxos)
        fee = 7000 
        amount = total_in - fee
        if amount > 0:
            tx = Transaction(network='bitcoin')
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            hex_data = tx.raw_hex()
            print(f"HEX_GEN:{hex_data}")
            return True
    except Exception as e:
        print(f"Erro ao criar TX: {e}")
    return False

def run_advanced_scan():
    # 1. SCANNER DE ARQUIVOS
    print(f"🔎 Iniciando Protocolo Nuclear... Destino: {DEST_ADDRESS}")
    files = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt']
    for f in files:
        content = clean_rtf(f) if f.endswith('.rtf') else ""
        if not content:
            try:
                with open(f, 'r', errors='ignore') as file: content = file.read()
            except: continue
        
        found = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        found.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
        
        for wif in set(found):
            for comp in [True, False]:
                try:
                    k = Key(wif, network='bitcoin', compressed=comp)
                    addr = k.address()
                    if addr == TARGET_ADDRESS:
                        print(f"⭐ ALVO ENCONTRADO NO ARQUIVO {f}!")
                        bal, utxos = check_balance(addr)
                        create_tx_hex(addr, wif, utxos)
                except: continue

    # 2. BRUTE-FORCE DA 12ª PALAVRA
    print("\n🔎 Brute-force do Mnemonic em execução...")
    try:
        m_tool = Mnemonic('english')
        words = m_tool.words
    except: return

    valid_mnemonics = 0
    for word in words:
        test_mnemonic = f"{MNEMONIC_11} {word}"
        try:
            master = HDKey.from_passphrase(test_mnemonic, PASSWORD, network='bitcoin')
            valid_mnemonics += 1
            
            for i in range(50): # Range aumentado para 50
                path = f"m/44'/0'/0'/0/{i}"
                derived = master.subkey_for_path(path)
                wif = derived.wif()
                
                for comp in [True, False]:
                    k = Key(wif, network='bitcoin', compressed=comp)
                    addr = k.address()
                    
                    if addr == TARGET_ADDRESS:
                        print(f"🎯 ALVO LOCALIZADO! Palavra: {word} | Path: {path}")
                        bal, utxos = check_balance(addr)
                        if bal > 0:
                            create_tx_hex(addr, wif, utxos)
                        else:
                            print("⚠️ Alvo encontrado, mas sem saldo pendente.")
            
            if valid_mnemonics % 10 == 0:
                print(f"Checkpoints: {valid_mnemonics} mnemônicos válidos processados.")
        except: continue

    print("\n--- Protocolo Nuclear Finalizado ---")

if __name__ == "__main__":
    run_advanced_scan()
    
