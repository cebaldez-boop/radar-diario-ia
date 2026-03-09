#!/bin/bash
# Radar Diário de IA - Parar serviços
# Uso: ./stop.sh

echo "⏹️  Parando Radar Diário de IA..."

if docker compose version &> /dev/null; then
    docker compose down
elif command -v docker-compose &> /dev/null; then
    docker-compose down
else
    echo "❌ Docker Compose não encontrado."
    exit 1
fi

echo "✅ Serviços parados."
