#!/bin/bash
# =============================================================
# Radar Diário de IA - Script de Instalação para MacBook
# =============================================================
# Este script configura todo o ambiente necessário.
# Execute: chmod +x setup.sh && ./setup.sh
# =============================================================

set -e

echo "=============================================="
echo "  Radar Diário de IA - Instalação"
echo "=============================================="
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função de log
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
log_error() { echo -e "${RED}[ERRO]${NC} $1"; }

# Verificar Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker não encontrado!"
        echo ""
        echo "Instale o Docker Desktop para Mac:"
        echo "  https://www.docker.com/products/docker-desktop/"
        echo ""
        echo "Após instalar, abra o Docker Desktop e aguarde ele iniciar."
        echo "Depois, execute este script novamente."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker não está rodando!"
        echo ""
        echo "Abra o Docker Desktop e aguarde ele iniciar."
        echo "Depois, execute este script novamente."
        exit 1
    fi

    log_info "Docker encontrado e rodando ✓"
}

# Verificar docker compose
check_docker_compose() {
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "docker compose não encontrado!"
        echo "Atualize o Docker Desktop para uma versão recente."
        exit 1
    fi

    log_info "Docker Compose encontrado ✓"
}

# Criar arquivo .env
setup_env() {
    if [ -f .env ]; then
        log_warn "Arquivo .env já existe. Pulando criação."
        echo "  Para reconfigurar, delete o .env e rode o setup novamente."
        return
    fi

    echo ""
    echo "=============================================="
    echo "  Configuração de API Keys e E-mail"
    echo "=============================================="
    echo ""

    # Gemini API Key
    echo "1. Chave da API do Gemini (obrigatório)"
    echo "   Obtenha em: https://aistudio.google.com/app/apikey"
    read -p "   Cole sua GEMINI_API_KEY: " gemini_key

    # Email
    echo ""
    echo "2. Configuração de e-mail (para receber relatórios)"
    echo "   Use uma 'Senha de App' do Gmail:"
    echo "   https://myaccount.google.com/apppasswords"
    read -p "   Seu e-mail Gmail: " email_sender
    read -sp "   Senha de App do Gmail: " email_password
    echo ""
    read -p "   E-mail para receber relatórios [cebaldez@gmail.com]: " email_recipient
    email_recipient=${email_recipient:-cebaldez@gmail.com}

    # n8n credentials
    echo ""
    echo "3. Credenciais do n8n (interface web)"
    read -p "   Usuário n8n [admin]: " n8n_user
    n8n_user=${n8n_user:-admin}
    read -sp "   Senha n8n [radar2026]: " n8n_pass
    n8n_pass=${n8n_pass:-radar2026}
    echo ""

    # Criar .env
    cat > .env << EOF
# Radar Diário de IA - Configuração
# Gerado por setup.sh em $(date)

GEMINI_API_KEY=${gemini_key}

EMAIL_SENDER=${email_sender}
EMAIL_PASSWORD=${email_password}
EMAIL_RECIPIENT=${email_recipient}
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

N8N_BASIC_AUTH_USER=${n8n_user}
N8N_BASIC_AUTH_PASSWORD=${n8n_pass}

WHISPER_MODEL=base
CRON_SCHEDULE=0 4 * * *
TZ=America/Chicago
EOF

    log_info "Arquivo .env criado ✓"
}

# Criar diretórios
setup_dirs() {
    mkdir -p data/audio data/transcripts data/reports n8n-data
    log_info "Diretórios criados ✓"
}

# Build e start
start_services() {
    echo ""
    echo "=============================================="
    echo "  Construindo e iniciando serviços..."
    echo "=============================================="
    echo ""

    $COMPOSE_CMD build --no-cache
    log_info "Build concluído ✓"

    $COMPOSE_CMD up -d
    log_info "Serviços iniciados ✓"

    # Aguardar serviços ficarem prontos
    echo ""
    log_info "Aguardando serviços ficarem prontos..."
    sleep 10

    # Verificar health
    if curl -s http://localhost:8000/health | grep -q "ok"; then
        log_info "Worker API rodando ✓"
    else
        log_warn "Worker API ainda não respondeu. Aguarde mais alguns segundos."
    fi
}

# Instruções finais
show_instructions() {
    echo ""
    echo "=============================================="
    echo "  ✅ Instalação Concluída!"
    echo "=============================================="
    echo ""
    echo "  🌐 n8n:        http://localhost:5678"
    echo "     Usuário:    ${n8n_user:-admin}"
    echo "     Senha:      (a que você configurou)"
    echo ""
    echo "  🔧 Worker API: http://localhost:8000"
    echo "     Docs:       http://localhost:8000/docs"
    echo ""
    echo "  📋 Próximos passos:"
    echo "     1. Abra http://localhost:5678 no navegador"
    echo "     2. Faça login no n8n"
    echo "     3. Importe o workflow: n8n-workflow.json"
    echo "        (Menu > Import from File)"
    echo "     4. Ative o workflow"
    echo ""
    echo "  🧪 Para testar agora:"
    echo "     curl -X POST http://localhost:8000/run-sync \\"
    echo "       -H 'Content-Type: application/json' \\"
    echo "       -d '{\"max_age_days\": 1, \"send_email\": true}'"
    echo ""
    echo "  📖 Comandos úteis:"
    echo "     Iniciar:  docker compose up -d"
    echo "     Parar:    docker compose down"
    echo "     Logs:     docker compose logs -f worker"
    echo "     Status:   curl http://localhost:8000/status"
    echo ""
}

# Executar
check_docker
check_docker_compose
setup_dirs
setup_env
start_services
show_instructions
