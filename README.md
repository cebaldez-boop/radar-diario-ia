# 📡 Radar Diário de IA

Sistema automatizado que monitora canais de YouTube sobre IA e negócios, gera resumos e oportunidades de aplicação prática para suas empresas — tudo rodando **100% local** no seu MacBook.

---

## 📋 O que o sistema faz

1. **Monitora até 15 canais de YouTube** de IA e negócios via RSS feeds.
2. **Identifica vídeos novos** (últimos 3 dias) e registra no banco local.
3. **Baixa o áudio** de cada vídeo novo (via `yt-dlp`).
4. **Transcreve o áudio** usando Gemini API (ou Whisper local como fallback).
5. **Gera resumos em português** com bullets destacando ferramentas, updates, estratégias e insights.
6. **Gera oportunidades de negócio** para 4 empresas:
   - **Orbitflow** (automações via Upwork)
   - **Primal DEcode** (canal YouTube sobre IA)
   - **Tranzit** (importação EUA→Brasil)
   - **NEXUS AI Solutions** (serviços de IA)
7. **Monta um relatório diário** completo em Markdown e HTML.
8. **Envia o relatório por e-mail** automaticamente.
9. **Salva tudo localmente** em banco SQLite.

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────┐
│              Docker Compose                  │
│                                              │
│  ┌──────────┐       ┌───────────────────┐   │
│  │   n8n    │──────▶│   Worker (Python)  │   │
│  │ :5678    │ HTTP  │   FastAPI :8000    │   │
│  │          │       │                    │   │
│  │ Schedule │       │ • RSS feeds        │   │
│  │ trigger  │       │ • yt-dlp download  │   │
│  └──────────┘       │ • Gemini API       │   │
│                     │ • Report generator │   │
│                     │ • Email sender     │   │
│                     │ • SQLite DB        │   │
│                     └───────────────────┘   │
│                              │               │
│                     ┌────────▼──────────┐   │
│                     │   /data (volume)   │   │
│                     │ • radar.db         │   │
│                     │ • audio/           │   │
│                     │ • reports/         │   │
│                     └───────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 🚀 Instalação Rápida

### Pré-requisitos

1. **Docker Desktop para Mac** — [Download aqui](https://www.docker.com/products/docker-desktop/)
2. **Chave da API do Gemini** — [Obter aqui](https://aistudio.google.com/app/apikey)
3. **Senha de App do Gmail** — [Configurar aqui](https://myaccount.google.com/apppasswords)

### Passo a passo

```bash
# 1. Clone ou copie o projeto para o seu Mac
cd ~/projetos  # ou qualquer pasta
# (copie os arquivos do projeto para cá)

# 2. Dê permissão aos scripts
chmod +x setup.sh start.sh stop.sh

# 3. Execute o setup interativo
./setup.sh
```

O script vai pedir:
- Sua chave da API do Gemini
- Seu e-mail e senha de app do Gmail
- Credenciais para o n8n (interface web)

Depois, ele constrói os containers e inicia tudo automaticamente.

---

## 🎮 Como Usar

### Ligar o sistema
```bash
./start.sh
# ou
docker compose up -d
```

### Desligar o sistema
```bash
./stop.sh
# ou
docker compose down
```

### Ver logs em tempo real
```bash
docker compose logs -f worker
```

### Executar o pipeline manualmente
```bash
# Via API (recomendado)
curl -X POST http://localhost:8000/run-sync \
  -H 'Content-Type: application/json' \
  -d '{"max_age_days": 3, "send_email": true}'

# Ou via n8n: abra http://localhost:5678, vá ao workflow e clique em "Execute"
```

### Ver status
```bash
curl http://localhost:8000/status
```

### Ver estatísticas
```bash
curl http://localhost:8000/stats
```

---

## ⚙️ Configurações

### Adicionar ou remover canais de YouTube

Edite o arquivo `config/channels.json`:

```json
{
  "channels": [
    {
      "name": "Nome do Canal",
      "channel_id": "UCxxxxx",
      "handle": "@handle",
      "language": "en",
      "category": "ai_news"
    }
  ]
}
```

**Como encontrar o Channel ID:**
1. Vá ao canal no YouTube
2. Clique em "About" (Sobre)
3. Clique em "Share Channel" > "Copy Channel ID"

Ou use: https://timeskip.io/tools/youtube-channel-id-finder

### Ajustar o horário do relatório

Edite o arquivo `.env`:

```bash
# Formato cron: minuto hora dia mês dia_semana
# Padrão: 22:00 Dallas/CST (= 04:00 UTC)
CRON_SCHEDULE=0 4 * * *

# Timezone
TZ=America/Chicago
```

Exemplos:
- `0 4 * * *` = 22:00 Dallas (padrão)
- `0 3 * * *` = 21:00 Dallas
- `0 12 * * *` = 06:00 Dallas
- `0 4 * * 1-5` = 22:00 Dallas, apenas dias úteis

Após editar, reinicie: `docker compose restart`

### Ajustar prompts de resumo e oportunidades

Edite o arquivo `config/prompts.json`. Os prompts são:

- `summary_prompt` — Como o resumo é gerado
- `opportunities_prompt` — Como as oportunidades são geradas
- `top3_prompt` — Como o Top 3 ações é selecionado

**Mantenha os placeholders** (`{title}`, `{channel}`, etc.) intactos.

### Alterar modelo de transcrição local

No `.env`:
```bash
# Opções: tiny, base, small, medium, large-v3
# Quanto maior, mais preciso, mas mais lento
WHISPER_MODEL=base
```

---

## 📁 Estrutura de Arquivos

```
radar-diario-ia/
├── docker-compose.yml      # Orquestração dos containers
├── Dockerfile.worker       # Container do worker Python
├── .env                    # Suas configurações (NÃO versionar)
├── .env.example            # Template de configuração
├── setup.sh                # Script de instalação
├── start.sh                # Ligar o sistema
├── stop.sh                 # Desligar o sistema
├── n8n-workflow.json        # Workflow para importar no n8n
├── config/
│   ├── channels.json       # Lista de canais monitorados
│   └── prompts.json        # Prompts para o LLM
├── scripts/
│   ├── api.py              # Servidor FastAPI
│   ├── main.py             # Orquestrador do pipeline
│   ├── feed_checker.py     # Verificação de RSS feeds
│   ├── audio_downloader.py # Download de áudio (yt-dlp)
│   ├── transcriber.py      # Transcrição (Gemini/Whisper)
│   ├── summarizer.py       # Resumo e oportunidades (Gemini)
│   ├── report_generator.py # Geração de relatórios
│   ├── email_sender.py     # Envio de e-mail
│   ├── database.py         # Operações SQLite
│   └── requirements.txt    # Dependências Python
├── templates/
│   └── report_template.html # Template do relatório
├── data/                    # Dados gerados (gitignore)
│   ├── radar.db            # Banco SQLite
│   ├── audio/              # Áudios temporários
│   ├── transcripts/        # Transcrições
│   └── reports/            # Relatórios gerados
└── n8n-data/               # Dados do n8n (gitignore)
```

---

## 📊 Estrutura do Relatório Diário

O relatório segue esta estrutura:

1. **Cabeçalho** — Data, número de vídeos analisados, total de oportunidades
2. **Resumo das novidades** — Lista de vídeos + resumo curto de cada
3. **Oportunidades para Orbitflow** — Tabela com oportunidades de automação
4. **Oportunidades para Primal DEcode** — Ideias de vídeos, séries, formatos
5. **Oportunidades para Tranzit** — Logística, operação, vendas, anúncios
6. **Oportunidades para NEXUS AI Solutions** — Novos serviços/produtos de IA
7. **Top 3 Ações para Amanhã** — Alto impacto + baixa dificuldade

Cada oportunidade inclui:
| Coluna | Descrição |
|---|---|
| Oportunidade | Nome curto |
| Descrição | O que é |
| Tipo | Automação, serviço, produto digital, conteúdo, melhoria interna |
| Impacto Esperado | Tempo, custo, receita, clientes, lucro |
| Dificuldade | 1 (fácil) a 5 (difícil) |
| Primeiro Passo | Ação concreta para começar |

---

## 💰 Custos

| Componente | Custo |
|---|---|
| n8n (self-hosted) | **Grátis** |
| Docker Desktop | **Grátis** |
| yt-dlp | **Grátis** |
| SQLite | **Grátis** |
| Gemini API (Flash) | ~$0.01-0.05/dia (15 vídeos) |
| Gmail SMTP | **Grátis** |
| **Total estimado** | **< $2/mês** |

O sistema usa Gemini 2.0 Flash, que tem pricing muito baixo. Para 15 vídeos/dia, o custo estimado é inferior a $2/mês.

---

## 🔧 Troubleshooting

### "Docker não encontrado"
Instale o Docker Desktop: https://www.docker.com/products/docker-desktop/

### "Falha na autenticação SMTP"
- Use uma **Senha de App** do Gmail, não sua senha normal
- Ative 2FA na sua conta Google: https://myaccount.google.com/security
- Crie uma senha de app: https://myaccount.google.com/apppasswords

### "GEMINI_API_KEY não configurada"
Edite o `.env` e adicione sua chave: `GEMINI_API_KEY=sua_chave_aqui`

### "yt-dlp falhou"
Atualize o container: `docker compose build --no-cache worker && docker compose up -d worker`

### Vídeo não foi transcrito
Verifique os logs: `docker compose logs worker | grep "Erro"`

Possíveis causas:
- Vídeo muito longo (>2h) — ajuste o limite em `audio_downloader.py`
- Áudio protegido — alguns vídeos bloqueiam download
- Erro de rede — o sistema tentará novamente na próxima execução

---

## 🔄 Clonar para outro Mac

1. Copie toda a pasta `radar-diario-ia/` para o novo Mac
2. Instale o Docker Desktop
3. Execute `./setup.sh` (vai pedir as credenciais novamente)
4. Pronto!

Os dados do banco SQLite estão em `data/radar.db`. Copie este arquivo se quiser manter o histórico.

---

## 📜 Canais Monitorados (padrão)

| # | Canal | Idioma | Categoria |
|---|---|---|---|
| 1 | The AI Daily Brief | EN | Notícias de IA |
| 2 | Notícias de IA | PT | Notícias de IA |
| 3 | TheAIGRID | EN | Notícias de IA |
| 4 | Matthew Berman | EN | Reviews de IA |
| 5 | Futurepedia | EN | Ferramentas de IA |
| 6 | Two Minute Papers | EN | Pesquisa de IA |
| 7 | Julian Goldie SEO | EN | IA + Negócios |
| 8 | iampauljames | EN | IA + Negócios |
| 9 | Greg Isenberg | EN | Startups |
| 10 | Primal DEcode | PT | Conteúdo de IA |
| 11 | AI Jason | EN | Tutoriais de IA |
| 12 | Fireship | EN | Tech News |
| 13 | Wes Roth | EN | Notícias de IA |
| 14 | David Shapiro | EN | IA + Filosofia |
| 15 | AI Explained | EN | Explicadores de IA |

---

## 📄 API Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/` | Status geral do sistema |
| GET | `/health` | Health check |
| POST | `/run` | Executar pipeline (background) |
| POST | `/run-sync` | Executar pipeline (síncrono) |
| GET | `/status` | Status da execução atual |
| GET | `/stats` | Estatísticas gerais |
| GET | `/videos/today` | Vídeos processados hoje |
| GET | `/opportunities/today` | Oportunidades de hoje |
| GET | `/report/{data}` | Relatório de uma data |

Documentação interativa: http://localhost:8000/docs

---

*Desenvolvido para Carlos Eduardo Baldez — Radar Diário de IA v1.0*
