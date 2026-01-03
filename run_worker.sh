#!/bin/bash

LOG_FILE="worker_${WORKER_ID}_output.txt"

echo "--------------------------------------------------"
echo "🚀 WORKER $WORKER_ID EM EXECUÇÃO"
echo "--------------------------------------------------"

# Executa Python e salva log em tempo real
python3 -u api_broadcast_system.py | tee "$LOG_FILE"

echo "--------------------------------------------------"
echo "📡 PROCESSANDO ENVIO DE TRANSAÇÕES (BROADCAST)..."
echo "--------------------------------------------------"

# Extrai o HEX do log e envia para as APIs
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read RAW_HEX; do
    if [ -n "$RAW_HEX" ]; then
        echo "⚡ Enviando transação detectada..."
        
        # Envio Blockchain.com
        RESP1=$(curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$RAW_HEX")
        echo "Blockchain.com: $RESP1"

        # Envio ViaBTC
        RESP2=$(curl -s -X POST https://www.viabtc.com/res/tools/v1/broadcast -d "raw_tx=$RAW_HEX")
        echo "ViaBTC: $RESP2"
    fi
done

echo "✅ WORKER $WORKER_ID FINALIZADO."
