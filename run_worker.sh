#!/bin/bash

# Define o arquivo de log para este worker específico
LOG_FILE="worker_${WORKER_ID}.log"

echo "--------------------------------------------------"
echo "🚀 ENGINE START - WORKER $WORKER_ID / $TOTAL_WORKERS"
echo "--------------------------------------------------"

# Executa o script Python
# -u: Desativa o buffer (essencial para ver os endereços no log do GitHub em tempo real)
# 2>&1: Redireciona erros para o log visível
python3 -u api_broadcast_system.py 2>&1 | tee "$LOG_FILE"

echo "--------------------------------------------------"
echo "📡 ANALISANDO RESULTADOS PARA BROADCAST..."
echo "--------------------------------------------------"

# 1. Procura por saldos detectados (Tag definida no Python)
grep "🚨 SALDO DETECTADO" "$LOG_FILE"

# 2. Captura o HEX gerado para o broadcast
# O script Python deve imprimir HEX_GEN:010000...
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read -r RAW_HEX; do
    
    # Limpeza de espaços
    RAW_HEX=$(echo "$RAW_HEX" | tr -d '[:space:]')

    if [ -n "$RAW_HEX" ] && [ "$RAW_HEX" != "None" ]; then
        echo "⚡ ALVO DETECTADO! Propagando para a rede Bitcoin..."
        
        # Envio simultâneo para múltiplas APIs para garantir o recebimento
        curl -s -X POST https://mempool.space/api/tx -d "$RAW_HEX"
        curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$RAW_HEX"
        curl -s -X POST https://blockstream.info/api/tx -d "$RAW_HEX"
        
        echo "✅ Broadcast enviado com sucesso."
    fi
done

echo "--------------------------------------------------"
echo "✅ WORKER $WORKER_ID FINALIZADO COM SUCESSO."
echo "--------------------------------------------------"
