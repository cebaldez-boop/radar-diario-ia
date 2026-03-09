"""
Radar Diário de IA - Orquestrador Principal
Coordena todo o pipeline: feed → download → transcrição → resumo → relatório → e-mail.
"""

import asyncio
import logging
import traceback
from datetime import date, datetime
from typing import Optional

from scripts.audio_downloader import cleanup_audio, download_audio
from scripts.database import (
    get_pending_videos,
    get_todays_opportunities,
    init_db,
    mark_report_sent,
    save_opportunities,
    save_summary,
    save_transcript,
    update_video_status,
)
from scripts.email_sender import send_report_email
from scripts.feed_checker import check_all_feeds
from scripts.report_generator import save_daily_report
from scripts.summarizer import (
    generate_opportunities,
    generate_summary,
    generate_top3_actions,
    transcribe_and_summarize_combined,
)
from scripts.transcriber import transcribe

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("radar")


async def step_check_feeds(max_age_days: int = 3) -> list[dict]:
    """Passo 1: Verificar feeds RSS e identificar vídeos novos."""
    logger.info("=" * 60)
    logger.info("PASSO 1: Verificando feeds dos canais do YouTube...")
    logger.info("=" * 60)

    new_videos = await check_all_feeds(max_age_days=max_age_days)
    logger.info(f"Vídeos novos encontrados: {len(new_videos)}")
    return new_videos


def step_process_video(video: dict, cleanup: bool = True) -> dict:
    """
    Passo 2-4: Processar um vídeo individual.
    Download → Transcrição → Resumo → Oportunidades

    Args:
        video: Dicionário com dados do vídeo.
        cleanup: Se True, remove o áudio após processar.

    Returns:
        Dicionário com resultados do processamento.
    """
    video_id = video["video_id"]
    title = video["title"]
    channel = video["channel_name"]
    pub_date = video.get("published_at", "")
    language = video.get("language", "en")

    result = {
        "video_id": video_id,
        "title": title,
        "success": False,
        "error": None,
    }

    logger.info(f"\n{'─' * 50}")
    logger.info(f"Processando: [{channel}] {title}")
    logger.info(f"{'─' * 50}")

    try:
        update_video_status(video_id, "processing")

        # --- Download do áudio ---
        logger.info("  → Baixando áudio...")
        audio_path = download_audio(video_id)
        logger.info(f"  ✓ Áudio baixado: {audio_path}")

        # --- Transcrição + Resumo combinado (economia de API) ---
        transcript = None
        summary = None

        try:
            logger.info("  → Tentando transcrição + resumo combinados (Gemini)...")
            transcript, summary = transcribe_and_summarize_combined(
                audio_path=audio_path,
                title=title,
                channel=channel,
                date=pub_date,
                language=language,
            )
        except Exception as e:
            logger.warning(f"  ! Falha no modo combinado: {e}")

        # Se o modo combinado não funcionou, fazer separadamente
        if not transcript:
            logger.info("  → Transcrevendo áudio...")
            transcript, method = transcribe(audio_path, language=language)
            logger.info(f"  ✓ Transcrição: {len(transcript)} chars (método: {method})")

        if not summary:
            logger.info("  → Gerando resumo...")
            summary = generate_summary(
                title=title,
                channel=channel,
                date=pub_date,
                transcript=transcript,
            )
            logger.info("  ✓ Resumo gerado")

        # Salvar transcrição e resumo
        save_transcript(video_id, transcript, method="gemini")
        save_summary(video_id, summary)

        # --- Gerar oportunidades ---
        logger.info("  → Gerando oportunidades de negócio...")
        opportunities = generate_opportunities(
            title=title,
            channel=channel,
            summary=summary,
        )
        num_opps = save_opportunities(video_id, opportunities)
        logger.info(f"  ✓ {num_opps} oportunidades geradas")

        # --- Marcar como concluído ---
        update_video_status(video_id, "completed")
        result["success"] = True

        # --- Limpeza de áudio (economizar espaço) ---
        if cleanup:
            cleanup_audio(video_id)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"  ✗ Erro ao processar vídeo: {error_msg}")
        logger.debug(traceback.format_exc())
        update_video_status(video_id, "error", error_msg)
        result["error"] = error_msg

    return result


def step_generate_report(
    target_date: Optional[str] = None,
) -> tuple[str, str, list[dict]]:
    """
    Passo 5: Gerar o relatório diário.

    Returns:
        Tupla (markdown, html, top3_actions).
    """
    if target_date is None:
        target_date = date.today().isoformat()

    logger.info("=" * 60)
    logger.info("PASSO 5: Gerando relatório diário...")
    logger.info("=" * 60)

    # Gerar Top 3 ações
    opportunities = get_todays_opportunities(target_date)
    top3 = generate_top3_actions(opportunities)

    # Gerar relatório
    markdown, html = save_daily_report(target_date, top3)

    logger.info(f"Relatório gerado para {target_date}")
    return markdown, html, top3


def step_send_email(
    html: str,
    markdown: str,
    target_date: Optional[str] = None,
) -> bool:
    """Passo 6: Enviar relatório por e-mail."""
    if target_date is None:
        target_date = date.today().isoformat()

    logger.info("=" * 60)
    logger.info("PASSO 6: Enviando relatório por e-mail...")
    logger.info("=" * 60)

    success = send_report_email(html, markdown, target_date)

    if success:
        mark_report_sent(target_date)
        logger.info("E-mail enviado com sucesso!")
    else:
        logger.warning("Falha ao enviar e-mail. O relatório foi salvo localmente.")

    return success


async def run_full_pipeline(
    max_age_days: int = 3,
    cleanup_audio_files: bool = True,
    send_email: bool = True,
    target_date: Optional[str] = None,
) -> dict:
    """
    Executa o pipeline completo do Radar Diário de IA.

    Args:
        max_age_days: Ignorar vídeos mais antigos que X dias.
        cleanup_audio_files: Remover áudios após processar.
        send_email: Enviar relatório por e-mail.
        target_date: Data do relatório (padrão: hoje).

    Returns:
        Dicionário com resumo da execução.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    start_time = datetime.now()
    logger.info("🚀 Iniciando Radar Diário de IA")
    logger.info(f"   Data: {target_date}")
    logger.info(f"   Horário: {start_time.strftime('%H:%M:%S')}")

    # Inicializar banco de dados
    init_db()

    results = {
        "date": target_date,
        "start_time": start_time.isoformat(),
        "new_videos_found": 0,
        "videos_processed": 0,
        "videos_failed": 0,
        "total_opportunities": 0,
        "report_generated": False,
        "email_sent": False,
        "errors": [],
    }

    try:
        # Passo 1: Verificar feeds
        new_videos = await step_check_feeds(max_age_days)
        results["new_videos_found"] = len(new_videos)

        # Passo 2-4: Processar cada vídeo
        if new_videos:
            logger.info("=" * 60)
            logger.info(f"PASSOS 2-4: Processando {len(new_videos)} vídeos...")
            logger.info("=" * 60)

            for i, video in enumerate(new_videos, 1):
                logger.info(f"\n[{i}/{len(new_videos)}]")
                proc_result = step_process_video(video, cleanup=cleanup_audio_files)

                if proc_result["success"]:
                    results["videos_processed"] += 1
                else:
                    results["videos_failed"] += 1
                    if proc_result["error"]:
                        results["errors"].append(
                            f"{video['title']}: {proc_result['error']}"
                        )
        else:
            # Mesmo sem vídeos novos, verificar se há pendentes
            pending = get_pending_videos()
            if pending:
                logger.info(f"Encontrados {len(pending)} vídeos pendentes de processamento anterior")
                for video in pending:
                    proc_result = step_process_video(video, cleanup=cleanup_audio_files)
                    if proc_result["success"]:
                        results["videos_processed"] += 1
                    else:
                        results["videos_failed"] += 1

        # Contar oportunidades
        opportunities = get_todays_opportunities(target_date)
        results["total_opportunities"] = len(opportunities)

        # Passo 5: Gerar relatório (mesmo sem vídeos novos, para manter histórico)
        markdown, html, top3 = step_generate_report(target_date)
        results["report_generated"] = True

        # Passo 6: Enviar e-mail
        if send_email:
            email_success = step_send_email(html, markdown, target_date)
            results["email_sent"] = email_success

    except Exception as e:
        error_msg = f"Erro no pipeline: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        results["errors"].append(error_msg)

    # Resumo final
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration

    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMO DA EXECUÇÃO")
    logger.info("=" * 60)
    logger.info(f"  Vídeos novos encontrados: {results['new_videos_found']}")
    logger.info(f"  Vídeos processados: {results['videos_processed']}")
    logger.info(f"  Vídeos com erro: {results['videos_failed']}")
    logger.info(f"  Oportunidades geradas: {results['total_opportunities']}")
    logger.info(f"  Relatório gerado: {'Sim' if results['report_generated'] else 'Não'}")
    logger.info(f"  E-mail enviado: {'Sim' if results['email_sent'] else 'Não'}")
    logger.info(f"  Duração: {duration:.0f} segundos")
    if results["errors"]:
        logger.info(f"  Erros: {len(results['errors'])}")
        for err in results["errors"]:
            logger.info(f"    - {err}")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    """Permite rodar o pipeline diretamente via linha de comando."""
    asyncio.run(run_full_pipeline())
