#!/bin/bash

# Define o nome do arquivo de log único para o Worker
LOG_FILE="worker_${WORKER_ID}.log"

echo "--------------------------------------------------"
echo "🚀 INICIANDO VARREDURA - WORKER $WORKER_ID"
echo "--------------------------------------------------"

# -u força o log em tempo real
python3 -u api_broadcast_system.py 2>&1 | tee "$LOG_FILE"

echo "--------------------------------------------------"
echo "📡 ANALISANDO RESULTADOS E BROADCAST..."
echo "--------------------------------------------------"

# Procura a tag de saldo e a chave gerada
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read -r PRIV_KEY; do
    if [ -n "$PRIV_KEY" ]; then
        echo "⚡ Saldo confirmado! Realizando broadcast da chave encontrada..."
        # Aqui o sistema pode disparar a transação
    fi
done

echo "✅ Worker $WORKER_ID finalizado."
