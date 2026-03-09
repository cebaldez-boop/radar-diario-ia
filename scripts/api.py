"""
Radar Diário de IA - API FastAPI
Servidor HTTP que expõe endpoints para o n8n e para uso manual.
"""

import logging
import os
from datetime import date, datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from scripts.database import get_stats, get_todays_opportunities, get_todays_videos, init_db
from scripts.main import run_full_pipeline

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("radar.api")

# Estado global
pipeline_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
}

# FastAPI app
app = FastAPI(
    title="Radar Diário de IA",
    description="API para o sistema de monitoramento diário de novidades em IA",
    version="1.0.0",
)

# Scheduler
scheduler = AsyncIOScheduler()


class RunRequest(BaseModel):
    """Parâmetros para execução manual do pipeline."""
    max_age_days: int = 3
    cleanup_audio: bool = True
    send_email: bool = True
    target_date: Optional[str] = None


class RunResponse(BaseModel):
    """Resposta da execução do pipeline."""
    status: str
    message: str
    result: Optional[dict] = None


@app.on_event("startup")
async def startup_event():
    """Inicialização do servidor."""
    logger.info("Iniciando Radar Diário de IA API...")

    # Inicializar banco de dados
    init_db()
    logger.info("Banco de dados inicializado")

    # Configurar agendamento
    cron_schedule = os.environ.get("CRON_SCHEDULE", "0 4 * * *")
    tz = os.environ.get("TZ", "America/Chicago")

    try:
        parts = cron_schedule.split()
        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone=tz,
            )
            scheduler.add_job(
                scheduled_run,
                trigger=trigger,
                id="daily_radar",
                name="Radar Diário de IA",
                replace_existing=True,
            )
            scheduler.start()
            logger.info(f"Agendamento configurado: {cron_schedule} ({tz})")
        else:
            logger.warning(f"Formato de cron inválido: {cron_schedule}")
    except Exception as e:
        logger.error(f"Erro ao configurar agendamento: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Encerramento do servidor."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("Servidor encerrado")


async def scheduled_run():
    """Execução agendada do pipeline."""
    logger.info("Execução agendada iniciada")
    await _run_pipeline(RunRequest())


async def _run_pipeline(request: RunRequest) -> dict:
    """Executa o pipeline com controle de concorrência."""
    if pipeline_status["running"]:
        return {
            "status": "busy",
            "message": "Pipeline já está em execução. Aguarde a conclusão.",
        }

    pipeline_status["running"] = True
    pipeline_status["last_run"] = datetime.now().isoformat()

    try:
        result = await run_full_pipeline(
            max_age_days=request.max_age_days,
            cleanup_audio_files=request.cleanup_audio,
            send_email=request.send_email,
            target_date=request.target_date,
        )
        pipeline_status["last_result"] = result
        return {
            "status": "success",
            "message": "Pipeline executado com sucesso",
            "result": result,
        }
    except Exception as e:
        error_result = {"status": "error", "message": str(e)}
        pipeline_status["last_result"] = error_result
        return error_result
    finally:
        pipeline_status["running"] = False


# -------------------------------------------------------
# Endpoints
# -------------------------------------------------------

@app.get("/")
async def root():
    """Página principal com status do sistema."""
    stats = get_stats()
    return {
        "system": "Radar Diário de IA",
        "version": "1.0.0",
        "status": "running" if pipeline_status["running"] else "idle",
        "last_run": pipeline_status["last_run"],
        "stats": stats,
    }


@app.get("/health")
async def health():
    """Health check para o n8n e Docker."""
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
async def run_pipeline(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Executa o pipeline completo.
    Use este endpoint para disparar manualmente ou via n8n.
    """
    if pipeline_status["running"]:
        raise HTTPException(
            status_code=409,
            detail="Pipeline já está em execução. Aguarde a conclusão.",
        )

    # Executar em background para não bloquear a resposta
    background_tasks.add_task(_run_pipeline, request)

    return RunResponse(
        status="started",
        message="Pipeline iniciado em background. Use GET /status para acompanhar.",
    )


@app.post("/run-sync")
async def run_pipeline_sync(request: RunRequest):
    """
    Executa o pipeline completo de forma síncrona (aguarda conclusão).
    Use este endpoint quando precisar do resultado imediato.
    """
    result = await _run_pipeline(request)
    return result


@app.get("/status")
async def get_status():
    """Retorna o status atual do pipeline."""
    return {
        "running": pipeline_status["running"],
        "last_run": pipeline_status["last_run"],
        "last_result": pipeline_status["last_result"],
    }


@app.get("/stats")
async def get_system_stats():
    """Retorna estatísticas do sistema."""
    return get_stats()


@app.get("/videos/today")
async def get_videos_today(target_date: Optional[str] = None):
    """Retorna os vídeos processados hoje."""
    videos = get_todays_videos(target_date)
    return {"date": target_date or date.today().isoformat(), "count": len(videos), "videos": videos}


@app.get("/opportunities/today")
async def get_opportunities_today(target_date: Optional[str] = None):
    """Retorna as oportunidades geradas hoje."""
    opps = get_todays_opportunities(target_date)
    return {"date": target_date or date.today().isoformat(), "count": len(opps), "opportunities": opps}


@app.get("/report/{target_date}")
async def get_report(target_date: str):
    """Retorna o relatório de uma data específica."""
    from scripts.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE report_date = ?", (target_date,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Relatório não encontrado para {target_date}")

    return dict(row)
