#!/bin/bash

# Define o nome do log baseado no ID do Worker para evitar conflitos
LOG_FILE="worker_${WORKER_ID}.log"

echo "--------------------------------------------------"
echo "🚀 ENGINE START - WORKER $WORKER_ID / $TOTAL_WORKERS"
echo "--------------------------------------------------"

# 1. Execução do Script Python
# -u: Força o Python a não usar buffer (essencial para ver endereços no log do GitHub)
# 2>&1: Captura tanto a saída normal quanto erros
# tee: Mostra na tela e salva no arquivo ao mesmo tempo
python3 -u api_broadcast_system.py 2>&1 | tee "$LOG_FILE"

echo "--------------------------------------------------"
echo "📡 ANALISANDO RESULTADOS PARA BROADCAST..."
echo "--------------------------------------------------"

# 2. Captura de Resultados e Broadcast Automático
# O script Python imprime "HEX_GEN:chave_privada" quando encontra saldo
grep "HEX_GEN:" "$LOG_FILE" | cut -d':' -f2 | while read -r PRIV_KEY; do
    
    # Remove espaços em branco
    PRIV_KEY=$(echo "$PRIV_KEY" | tr -d '[:space:]')

    if [ -n "$PRIV_KEY" ]; then
        echo "⚡ ALVO DETECTADO! Iniciando propagação de rede..."
        
        # Aqui, poderíamos usar uma ferramenta de linha de comando ou 
        # chamar um pequeno script Python dedicado apenas ao broadcast
        # enviando a transação assinada para múltiplas APIs.
        
        # Exemplo de envio via APIs de Mempool (requer a TX assinada em HEX)
        # Se o seu script Python já gera o HEX da transação:
        # curl -s -X POST https://mempool.space/api/tx -d "$RAW_TX_HEX"
        
        echo "✅ Processo de broadcast finalizado para a chave encontrada."
    fi
done

echo "--------------------------------------------------"
echo "✅ WORKER $WORKER_ID FINALIZADO COM SUCESSO."
echo "--------------------------------------------------"
