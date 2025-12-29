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
    """Extrai apenas texto puro de um arquivo RTF rudimentar"""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Remove comandos RTF comuns (backslash commands)
            clean_text = re.sub(r'\\[a-z0-9]+(?:\s|-?\d+)?', '', content)
            # Remove chaves de formatação
            clean_text = re.sub(r'[{}]', '', clean_text)
            return clean_text
    except:
        return ""

def check_balance(address):
    try:
        r = requests.get(f"https://mempool.space/api/address/{address}/utxo", timeout=2)
        if r.status_code == 200 and r.json():
            return sum(u['value'] for u in r.json()), r.json()
    except: pass
    return 0, []

def run_advanced_scan():
    all_keys = []
    
    # 1. BUSCA EM ARQUIVOS (Incluindo RTF)
    print("🔎 Vasculhando arquivos em busca de chaves...")
    files = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt']
    for f in files:
        content = clean_rtf(f) if f.endswith('.rtf') else ""
        if not content:
            try:
                with open(f, 'r', errors='ignore') as file: content = file.read()
            except: continue
        
        # Procura por WIFs (5, L ou K) e Hex (64 chars)
        found_wif = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        found_hex = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
        all_keys.extend(found_wif + found_hex)
    
    all_keys = list(set(all_keys))
    if all_keys:
        print(f"✅ {len(all_keys)} chaves encontradas nos arquivos. Verificando...")
        for wif in all_keys:
            for comp in [True, False]:
                try:
                    k = Key(wif, network='bitcoin', compressed=comp)
                    if k.address() == TARGET_ADDRESS:
                        print(f"⭐ ALVO ENCONTRADO EM ARQUIVO! WIF: {wif}")
                except: continue

    # 2. BRUTE-FORCE DA 12ª PALAVRA (Correção de Checksum)
    print("\n🔎 Iniciando Brute-force do Mnemonic (12ª palavra)...")
    words = Mnemonic().wordlist('english')
    for word in words:
        test_mnemonic = f"{MNEMONIC_11} {word}"
        try:
            master = HDKey.from_passphrase(test_mnemonic, PASSWORD, network='bitcoin')
            # Se não deu erro de checksum, a palavra é válida
            print(f"Palavra válida: {word}. Testando derivações...")
            
            for purpose in [44, 49, 84]:
                for i in range(100):
                    path = f"m/{purpose}'/0'/0'/0/{i}"
                    derived = master.subkey_for_path(path)
                    wif = derived.wif()
                    
                    for comp in [True, False]:
                        k = Key(wif, network='bitcoin', compressed=comp)
                        # Checa formato conforme purpose
                        if purpose == 44: addr = k.address()
                        elif purpose == 49: addr = k.address(witness_type='p2sh-p2wpkh')
                        else: addr = k.address(witness_type='p2wpkh')

                        if addr == TARGET_ADDRESS:
                            print(f"⭐ !!! ALVO ENCONTRADO !!! Palavra: {word} | Path: {path} | WIF: {wif}")
                            
                        # Opcional: checar saldo real de qualquer endereço gerado
                        # bal, utxos = check_balance(addr)
                        # if bal > 0: print(f"💰 SALDO em {addr}: {bal} sats")
        except:
            continue

if __name__ == "__main__":
    run_advanced_scan()
