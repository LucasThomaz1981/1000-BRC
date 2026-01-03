#!/bin/bash

# Nome do arquivo de log deste worker
WORK_LOG="log_worker_${WORKER_ID}.txt"

echo "--------------------------------------------------"
echo "🚀 INICIANDO WORKER $WORKER_ID"
echo "--------------------------------------------------"

# Executa o Python em modo 'unbuffered' (-u) para o Shell ler em tempo real
# O 'tee' garante que você veja o progresso no console do GitHub
python3 -u api_broadcast_system.py | tee "$WORK_LOG"

echo "--------------------------------------------------"
echo "🔍 VARREDURA CONCLUÍDA. PROCESSANDO BROADCASTS..."
echo "--------------------------------------------------"

# Procura as linhas HEX_GEN geradas pelo Python
grep "HEX_GEN:" "$WORK_LOG" | cut -d':' -f2 | while read HEX_DATA; do
    if [ -n "$HEX_DATA" ]; then
        echo "📡 Transação Assinada Detectada!"
        
        # 1. Broadcast via Blockchain.com
        echo "🌐 Tentando Blockchain.com..."
        RESPONSE_BC=$(curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$HEX_DATA")
        echo "Resposta Blockchain: $RESPONSE_BC"

        # 2. Broadcast via ViaBTC (Excelente para taxas customizadas)
        echo "🌐 Tentando ViaBTC..."
        RESPONSE_VIA=$(curl -s -X POST https://www.viabtc.com/res/tools/v1/broadcast -d "raw_tx=$HEX_DATA")
        echo "Resposta ViaBTC: $RESPONSE_VIA"
        
        echo "--------------------------------------------------"
    fi
done

echo "✅ PROCESSO DO WORKER $WORKER_ID FINALIZADO."
