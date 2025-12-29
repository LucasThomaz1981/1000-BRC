import requests
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.mnemonic import Mnemonic

# --- CONFIGURAÇÕES ---
TARGET_ADDRESS = "1HYfivTqoSzjqy6eawyitWoK8HvigtU3yb"
PASSWORD = "Benjamin2020*1981$"
# As 11 palavras iniciais (removi a 12ª 'such' para testar todas)
MNEMONIC_11 = "tree dwarf rubber off tree finger hair hope emerge earn friend"
DEST_ADDRESS = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'

def check_balance(address):
    try:
        r = requests.get(f"https://mempool.space/api/address/{address}/utxo", timeout=2)
        if r.status_code == 200:
            utxos = r.json()
            if utxos:
                return sum(u['value'] for u in utxos), utxos
    except: pass
    return 0, []

def run_bruteforce_checksum():
    words = Mnemonic().wordlist('english')
    print(f"🔎 Iniciando Brute-force da 12ª palavra...")
    
    found_any = False
    
    for word in words:
        test_mnemonic = f"{MNEMONIC_11} {word}"
        try:
            # Tenta gerar a chave. Se o checksum for inválido, o bitcoinlib lança erro
            master = HDKey.from_passphrase(test_mnemonic, PASSWORD, network='bitcoin')
            
            # Se chegou aqui, a palavra é válida!
            print(f"\n✅ Checksum Válido encontrado: '{word}'")
            print(f"Tentando caminhos para: {test_mnemonic}")
            
            # Varredura rápida para esta combinação
            for purpose in [44, 49, 84]:
                for i in range(50): # Testamos os primeiros 50 índices por palavra válida
                    path = f"m/{purpose}'/0'/0'/0/{i}"
                    derived = master.subkey_for_path(path)
                    wif = derived.wif()
                    
                    for comp in [True, False]:
                        k = Key(wif, network='bitcoin', compressed=comp)
                        # Define formato conforme o propósito
                        if purpose == 44: addr = k.address()
                        elif purpose == 49: addr = k.address(witness_type='p2sh-p2wpkh')
                        else: addr = k.address(witness_type='p2wpkh')

                        if addr == TARGET_ADDRESS:
                            print(f"⭐ !!! ALVO ENCONTRADO !!! Palavra: {word} | Path: {path}")
                            print(f"WIF: {wif}")
                        
                        # Opcional: checar saldo real
                        # balance, utxos = check_balance(addr)
                        # if balance > 0: print(f"💰 SALDO em {addr}...")

        except Exception:
            # Se o checksum for inválido, ele apenas pula para a próxima palavra
            continue

    print("\n--- Fim da busca por checksums ---")

if __name__ == "__main__":
    run_bruteforce_checksum()
            
