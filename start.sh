#!/bin/bash
# Radar Diário de IA - Iniciar serviços
# Uso: ./start.sh

echo "🚀 Iniciando Radar Diário de IA..."

if docker compose version &> /dev/null; then
    docker compose up -d
elif command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    echo "❌ Docker Compose não encontrado. Instale o Docker Desktop."
    exit 1
fi

echo ""
echo "✅ Serviços iniciados!"
echo "   n8n:        http://localhost:5678"
echo "   Worker API: http://localhost:8000"
echo "   API Docs:   http://localhost:8000/docs"
