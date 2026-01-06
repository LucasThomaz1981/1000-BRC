#!/bin/bash
LOG_FILE="worker_${WORKER_ID}.log"

echo "--------------------------------------------------"
echo "🚀 INICIANDO ENGINE - WORKER $WORKER_ID"
echo "--------------------------------------------------"

# 1. Detecção Inteligente de Script
PYTHON_SCRIPT=""
if [ -f "api_broadcast_system.py" ]; then
    PYTHON_SCRIPT="api_broadcast_system.py"
elif [ -f "fdr_unified_system.py" ]; then
    PYTHON_SCRIPT="fdr_unified_system.py"
fi

# 2. Execução com Saída em Tempo Real
if [ -n "$PYTHON_SCRIPT" ]; then
    echo "📦 Script ativo: $PYTHON_SCRIPT"
    echo "🔍 Verificando integridade do Pool..."
    
    if [ -f "MASTER_POOL.txt" ]; then
        echo "✅ MASTER_POOL.txt detectado. Iniciando varredura distribuída..."
    else
        echo "⚠️ MASTER_POOL.txt não encontrado. O script tentará varredura direta."
    fi

    # Executa Python com -u (unbuffered) para garantir que os logs apareçam no GitHub
    python3 -u "$PYTHON_SCRIPT" 2>&1 | tee "$LOG_FILE"
else
    echo "❌ ERRO: Nenhum motor de varredura encontrado!"
    exit 1
fi

echo "--------------------------------------------------"
echo "📡 PROCESSANDO RESULTADOS DE BROADCAST..."
echo "--------------------------------------------------"

# 3. Extração de HEX e Envio para Múltiplas APIs
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read -r RAW_HEX; do
    RAW_HEX=$(echo "$RAW_HEX" | tr -d '[:space:]')
    
    if [ -n "$RAW_HEX" ]; then
        echo "⚡ ALVO CONFIRMADO! Propagando transação..."
        
        # Envio paralelo para máxima velocidade
        curl -s -X POST https://mempool.space/api/tx -d "$RAW_HEX" &
        curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$RAW_HEX" &
        curl -s -X POST https://blockstream.info/api/tx -d "$RAW_HEX" &
        
        wait
        echo "✅ Transação enviada para Mempool, Blockchain.info e Blockstream."
    fi
done

echo "--------------------------------------------------"
echo "✅ WORKER $WORKER_ID CONCLUÍDO."
echo "--------------------------------------------------"
