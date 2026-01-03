#!/bin/bash

echo "Worker iniciado: Varredura e Broadcast"

# 1. Executa o python com -u (unbuffered) para o grep ler em tempo real
# Redirecionamos a saída para um arquivo e para o console simultaneamente
python3 -u api_broadcast_system.py | tee output.txt

echo "------------------------------------------"
echo "Processando HEX encontrados..."

# 2. Filtra os HEX_GEN gerados e tenta o broadcast
grep "HEX_GEN:" output.txt | cut -d':' -f2 | while read HEX; do
    if [ -n "$HEX" ]; then
        echo "🚀 Transação detectada! Enviando..."

        # Tentativa 1: ViaBTC
        echo "Tentando ViaBTC..."
        RESP1=$(curl -s -X POST https://www.viabtc.com/res/tools/v1/broadcast -d "raw_tx=$HEX")
        echo "Resposta ViaBTC: $RESP1"

        # Tentativa 2: Blockchain.com
        echo "Tentando Blockchain.com..."
        RESP2=$(curl -s -X POST https://api.blockchain.info/pushtx -d "tx=$HEX")
        echo "Resposta Blockchain: $RESP2"
    fi
done

echo "Processo concluído."
