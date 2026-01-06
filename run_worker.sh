#!/bin/bash
LOG_FILE="worker_${WORKER_ID}.log"

echo "--------------------------------------------------"
echo "🚀 INICIANDO ENGINE - WORKER $WORKER_ID"
echo "--------------------------------------------------"

# 1. Identificar qual script Python está presente no repositório
PYTHON_SCRIPT=""

if [ -f "fdr_unified_system.py" ]; then
    PYTHON_SCRIPT="fdr_unified_system.py"
elif [ -f "api_broadcast_system.py" ]; then
    PYTHON_SCRIPT="api_broadcast_system.py"
fi

# 2. Execução Condicional
if [ -n "$PYTHON_SCRIPT" ]; then
    echo "📦 Script encontrado: $PYTHON_SCRIPT"
    echo "🔍 Iniciando varredura..."
    # Executa com -u para log em tempo real
    python3 -u "$PYTHON_SCRIPT" | tee "$LOG_FILE"
else
    echo "❌ ERRO: Nenhum script Python encontrado (fdr_unified ou api_broadcast)!"
    exit 1
fi

echo "--------------------------------------------------"
echo "📡 VERIFICANDO RESULTADOS PARA BROADCAST..."
echo "--------------------------------------------------"

# 3. Processamento do HEX e Broadcast Global
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read RAW_HEX; do
    # Limpeza de caracteres e espaços
    RAW_HEX=$(echo $RAW_HEX | tr -d '[:space:]')

    if [ -n "$RAW_HEX" ] && [ "$RAW_HEX" != "0100000001..." ]; then
        echo "⚡ ALVO DETECTADO! Propagando para a rede Bitcoin..."
        
        # Envio simultâneo para as 3 maiores APIs
        curl -s -X POST https://mempool.space/api/tx -d "$RAW_HEX"
        curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$RAW_HEX"
        curl -s -X POST https://blockstream.info/api/tx -d "$RAW_HEX"
        
        echo "✅ Broadcast concluído."
    fi
done

echo "--------------------------------------------------"
echo "✅ WORKER $WORKER_ID FINALIZADO."
echo "--------------------------------------------------"
