import requests
import re
import time

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
FILES_TO_SCAN = [
    'privatekeys.txt', 
    'priv.key.rtf', 
    'chavprivelet1.txt', 
    'chaves_extraidas_e_enderecos_1.txt',
    'enderecos.txt'
]

def check_balance(address):
    """Consulta saldo com fallback e retry"""
    apis = [
        f"https://mempool.space/api/address/{address}",
        f"https://blockstream.info/api/address/{address}"
    ]
    for api in apis:
        try:
            r = requests.get(api, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # Soma saldo confirmado e não confirmado (mempool/blockstream format)
                stats = data.get('chain_stats', {})
                mempool = data.get('mempool_stats', {})
                balance = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                unconfirmed = mempool.get('funded_txo_sum', 0) - mempool.get('spent_txo_sum', 0)
                return balance + unconfirmed
        except: continue
    return 0

def clean_content(raw_data):
    """Remove códigos RTF e limpa ruído de texto"""
    # Remove comandos RTF como \par, \tab, \lang1046
    clean = re.sub(r'\\[a-z0-9]+(?:\s|-?\d+)?', '', raw_data)
    # Remove chaves e caracteres especiais de formatação
    clean = re.sub(r'[{}]', '', clean)
    # Remove espaços extras e quebras de linha duplicadas
    return clean

def run_power_scan():
    print("☢️ INICIANDO VARREDURA POTENCIALIZADA (PROTOCOLO TOTAL)")
    
    all_addresses = set()
    all_keys = set()

    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                raw_content = f.read()
                content = clean_content(raw_content)
                
                # 1. Busca Endereços Públicos (Legacy, SegWit, Bech32)
                found_addr = re.findall(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b', content)
                found_bech = re.findall(r'\bbc1[a-z0-9]{39,59}\b', content)
                all_addresses.update(found_addr + found_bech)

                # 2. Busca Chaves Privadas (WIF e HEX)
                found_wif = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
                found_hex = re.findall(r'\b[0-9a-fA-F]{64}\b', content)
                all_keys.update(found_wif + found_hex)

                if found_addr or found_bech or found_wif:
                    print(f"📂 Arquivo {file_path} processado. Itens detectados.")
        except: continue

    print(f"📊 Resumo: {len(all_addresses)} endereços e {len(all_keys)} chaves únicas encontradas.")

    # Verificação de Saldos em Endereços Públicos Detectados
    print("\n🧐 Verificando saldos em endereços públicos...")
    for addr in all_addresses:
        bal = check_balance(addr)
        if bal > 0:
            print(f"🚨 ALERTA: ENDEREÇO COM SALDO ENCONTRADO: {addr} | Saldo: {bal} sats")
            # Salva em arquivo para auditoria manual imediata
            with open("alvos_com_saldo.txt", "a") as log:
                log.write(f"Endereço: {addr} | Saldo: {bal}\n")
        time.sleep(0.5)

    # Verificação de Saldos em Chaves Privadas (tentando derivar endereços)
    if all_keys:
        print("\n🔑 Verificando chaves privadas...")
        # (Lógica de derivação de Key(wif) e check_balance aqui como na versão anterior)
