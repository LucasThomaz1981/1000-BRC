#!/bin/bash

LOG_FILE="worker_${WORKER_ID}.log"

echo "--------------------------------------------------"
echo "🚀 INICIANDO VARREDURA - WORKER $WORKER_ID"
echo "--------------------------------------------------"

# -u desativa o buffer para mostrar endereços na hora
python3 -u api_broadcast_system.py 2>&1 | tee "$LOG_FILE"

echo "--------------------------------------------------"
echo "📡 ANALISANDO RESULTADOS FINAIS..."
echo "--------------------------------------------------"

# Procura por chaves com saldo detectado
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read -r PRIV_KEY; do
    if [ -n "$PRIV_KEY" ]; then
        echo "⚡ SALDO CONFIRMADO! Tentando broadcast da chave encontrada..."
        # Lógica de broadcast pode ser inserida aqui chamando um script de sign/push
    fi
done

echo "✅ Worker $WORKER_ID concluído."
