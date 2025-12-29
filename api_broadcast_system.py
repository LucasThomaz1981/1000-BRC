import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
TARGET_ADDRESS = "1HYfivTqoSzjqy6eawyitWoK8HvigtU3yb"
PASSWORD = "Benjamin2020*1981$" # Esta é a sua "Salt" do BIP39
DEST_ADDRESS = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'

def scan_final_v28():
    all_keys = []
    
    # 1. Fontes de Arquivo
    files = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                # Busca WIFs e Hexadecimais
                found = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
                found.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
                if found:
                    print(f"Sucesso: {len(found)} chaves de {f}")
                    all_keys.extend(found)
        except Exception: continue

    # 2. Derivação HD Corrigida
    try:
        mnemonic = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        print(f"Derivando caminhos com a Passphrase...")
        
        # Criando a Master Key a partir do Mnemonic + Passphrase (Salt)
        master = HDKey.from_passphrase(mnemonic, salt=PASSWORD, network='bitcoin')
        
        for i in range(200): # Aumentei o range para 200
            # Adicionando caminhos Legacy, SegWit e Native SegWit
            paths = [f"m/44'/0'/0'/0/{i}", f"m/49'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]
            for path in paths:
                derived_key = master.subkey_for_path(path)
                all_keys.append(derived_key.wif())
    except Exception as e:
        print(f"Erro na derivação: {e}")

    all_keys = list(set(all_keys))
    print(f"Iniciando varredura em {len(all_keys)} chaves...")

    for wif in all_keys:
        try:
            # Testar formatos Comprimidos e Não-Comprimidos
            for is_compressed in [True, False]:
                k = Key(wif, network='bitcoin', compressed=is_compressed)
                
                # O endereço alvo '1HYfi' é Legacy (P2PKH)
                addr = k.address() 
                
                if addr == TARGET_ADDRESS:
                    print(f"!!! ALVO DETECTADO: {addr} !!!")
                    print(f"WIF: {wif} | Comprimida: {is_compressed}")

                # Verificação de Saldo via API
                r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=5)
                if r.status_code == 200 and r.json():
                    utxos = r.json()
                    total_balance = sum(u['value'] for u in utxos)
                    print(f"!!! SALDO ENCONTRADO EM {addr}: {total_balance} sats !!!")
                    
                    # Lógica de Transação (Opcional automatizar aqui ou apenas exibir o HEX)
                    # ... (seu código de transação aqui)
            
        except Exception:
            continue

if __name__ == "__main__":
    scan_final_v28()
