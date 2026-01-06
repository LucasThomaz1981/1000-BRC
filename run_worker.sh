#!/bin/bash

# Define o arquivo de log temporário para este Worker
# O uso do WORKER_ID no nome ajuda a identificar logs em paralelo
LOG_FILE="worker_${WORKER_ID}_output.log"

echo "--------------------------------------------------"
echo "🚀 EXECUTANDO ENGINE PYTHON (WORKER $WORKER_ID)"
echo "--------------------------------------------------"

# Executa o Python com -u (unbuffered) para garantir saída em tempo real.
# Importante: O nome do script deve ser exatamente api_broadcast_system.py
python3 -u api_broadcast_system.py | tee "$LOG_FILE"

echo "--------------------------------------------------"
echo "📡 VERIFICANDO RESULTADOS PARA BROADCAST..."
echo "--------------------------------------------------"

# O Bash varre o log em busca da flag "HEX_GEN:" impressa pelo Python
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read RAW_HEX; do
    # Remove espaços em branco, quebras de linha ou retornos de carro indesejados
    RAW_HEX=$(echo $RAW_HEX | tr -d '[:space:]')

    # Verifica se o HEX é válido e não é o placeholder de exemplo
    if [ -n "$RAW_HEX" ] && [ "$RAW_HEX" != "0100000001..." ]; then
        echo "⚡ ALVO CONFIRMADO! Iniciando Broadcast Global..."
        
        # 1. Mempool.space (Principal)
        echo "🛰️ Enviando para Mempool.space..."
        RESPONSE1=$(curl -s -X POST https://mempool.space/api/tx -d "$RAW_HEX")
        echo "Resposta: $RESPONSE1"

        # 2. Blockchain.info
        echo "🛰️ Enviando para Blockchain.info..."
        RESPONSE2=$(curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$RAW_HEX")
        echo "Resposta: $RESPONSE2"
        
        # 3. Blockstream.info
        echo "🛰️ Enviando para Blockstream.info..."
        RESPONSE3=$(curl -s -X POST https://blockstream.info/api/tx -d "$RAW_HEX")
        echo "Resposta: $RESPONSE3"
    fi
done

echo "--------------------------------------------------"
echo "✅ WORKER $WORKER_ID FINALIZADO."
echo "--------------------------------------------------"
