#!/bin/bash

# Define o nome do arquivo de saída temporário para este worker específico
OUTPUT_FILE="output_worker_${WORKER_ID}.txt"

echo "--------------------------------------------------"
echo "🚀 WORKER $WORKER_ID: Iniciando Processamento..."
echo "--------------------------------------------------"

# Executa o Python com -u (unbuffered) para garantir que o Shell leia as linhas instantaneamente
# O 'tee' permite que você veja o log no GitHub e salve no arquivo ao mesmo tempo
python3 -u api_broadcast_system.py | tee "$OUTPUT_FILE"

echo "--------------------------------------------------"
echo "🔍 WORKER $WORKER_ID: Varredura concluída. Verificando HEX_GEN..."

# Busca por transações geradas no arquivo de saída
grep "HEX_GEN:" "$OUTPUT_FILE" | cut -d':' -f2 | while read HEX; do
    if [ -n "$HEX" ]; then
        echo "💰 Transação encontrada! Iniciando Broadcast na rede..."

        # Tentativa 1: ViaBTC
        echo "📡 Enviando para ViaBTC..."
        RESP1=$(curl -s -X POST https://www.viabtc.com/res/tools/v1/broadcast -d "raw_tx=$HEX")
        echo "Retorno ViaBTC: $RESP1"

        # Tentativa 2: Blockchain.com
        echo "📡 Enviando para Blockchain.com..."
        RESP2=$(curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$HEX")
        echo "Retorno Blockchain: $RESP2"
    fi
done

echo "✅ WORKER $WORKER_ID Finalizado."
