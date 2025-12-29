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
DEST_ADDRESS = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'

def clean_rtf(filename):
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            clean_text = re.sub(r'\\[a-z0-9]+(?:\s|-?\d+)?', '', content)
            clean_text = re.sub(r'[{}]', '', clean_text)
            return clean_text
    except: return ""

def run_advanced_scan():
    # 1. BUSCA EM ARQUIVOS
    print("🔎 Vasculhando arquivos...")
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
                    if k.address() == TARGET_ADDRESS:
                        print(f"⭐ ALVO ENCONTRADO EM ARQUIVO: {f}! WIF: {wif}")
                except: continue

    # 2. BRUTE-FORCE DA 12ª PALAVRA
    print("\n🔎 Iniciando Brute-force do Mnemonic...")
    # Correção do erro da Wordlist
    m_tool = Mnemonic('english')
    words = m_tool.words
    
    valid_count = 0
    for word in words:
        test_mnemonic = f"{MNEMONIC_11} {word}"
        try:
            # Validação rápida de checksum antes de derivar
            master = HDKey.from_passphrase(test_mnemonic, PASSWORD, network='bitcoin')
            
            # Se chegou aqui, o checksum é válido
            valid_count += 1
            print(f"[{valid_count}] Palavra válida: {word}. Testando caminhos...")
            
            for purpose in [44, 49, 84]:
                for i in range(100):
                    path = f"m/{purpose}'/0'/0'/0/{i}"
                    derived = master.subkey_for_path(path)
                    wif = derived.wif()
                    
                    for comp in [True, False]:
                        k = Key(wif, network='bitcoin', compressed=comp)
                        if purpose == 44: addr = k.address()
                        elif purpose == 49: addr = k.address(witness_type='p2sh-p2wpkh')
                        else: addr = k.address(witness_type='p2wpkh')

                        if addr == TARGET_ADDRESS:
                            print(f"⭐ !!! ALVO ENCONTRADO !!!")
                            print(f"Palavra: {word} | Path: {path} | WIF: {wif}")
                            # Aqui você pode adicionar a lógica de gerar o HEX se desejar
        except:
            continue

    print(f"\n--- Varredura finalizada. {valid_count} mnemônicos válidos testados. ---")

if __name__ == "__main__":
    run_advanced_scan()
