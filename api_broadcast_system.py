import requests
import time
from bitcoinlib.keys import Key, HDKey

# --- CONFIGURAÇÕES ---
TARGET_ADDRESS = "1HYfivTqoSzjqy6eawyitWoK8HvigtU3yb"
PASSWORD = "Benjamin2020*1981$"
MNEMONIC = "tree dwarf rubber off tree finger hair hope emerge earn friend such"

def check_balance(address):
    """Consulta se um endereço tem saldo via API do Mempool."""
    try:
        r = requests.get(f"https://mempool.space/api/address/{address}/utxo", timeout=5)
        if r.status_code == 200:
            utxos = r.json()
            if utxos:
                total = sum(u['value'] for u in utxos)
                return total
    except:
        pass
    return 0

def deep_balance_scan():
    try:
        master = HDKey.from_passphrase(MNEMONIC, passphrase=PASSWORD, network='bitcoin')
        print(f"Iniciando varredura de saldo... (Isso pode levar tempo devido às consultas de API)")

        # Testaremos as 2 contas mais prováveis e os primeiros 100 endereços de cada
        for account in range(2):
            for change in [0, 1]:
                type_str = "Recebimento" if change == 0 else "Troco"
                print(f"\nVerificando Conta {account} - {type_str}...")
                
                for i in range(100):
                    path = f"m/44'/0'/{account}'/{change}/{i}"
                    wif = master.subkey_for_path(path).wif()
                    
                    # Testamos sempre o formato Comprimido (padrão moderno) 
                    # e o Não-Comprimido (padrão antigo)
                    for comp in [True, False]:
                        k = Key(wif, network='bitcoin', compressed=comp)
                        addr = k.address()
                        
                        # 1. Verificação do Alvo Principal
                        if addr == TARGET_ADDRESS:
                            print(f"✅ ALVO PRINCIPAL ENCONTRADO: {addr} no caminho {path}")
                        
                        # 2. Verificação de qualquer saldo (Audit)
                        balance = check_balance(addr)
                        if balance > 0:
                            print(f"💰 SALDO DETECTADO! Endereço: {addr} | Valor: {balance} sats | WIF: {wif}")
                            with open("descobertas.txt", "a") as f:
                                f.write(f"Endereço: {addr} | Saldo: {balance} | WIF: {wif} | Path: {path}\n")

                    # Pequena pausa para evitar bloqueio da API (Rate Limit)
                    time.sleep(0.2) 
                    
                    if i % 20 == 0:
                        print(f"  Índice {i} verificado...")

        print("\nVarredura de saldo concluída. Verifique o arquivo 'descobertas.txt'.")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    deep_balance_scan()
