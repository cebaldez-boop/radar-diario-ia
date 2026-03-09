"""
Radar Diário de IA - Módulo de Verificação de Feeds RSS
Busca novos vídeos dos canais do YouTube via RSS feeds.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from scripts.database import insert_video, video_exists

logger = logging.getLogger(__name__)

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config/channels.json")


def load_channels() -> list[dict]:
    """Carrega a lista de canais do arquivo de configuração."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("channels", [])


async def fetch_feed(channel_id: str, channel_name: str) -> list[dict]:
    """
    Busca o feed RSS de um canal do YouTube.
    Retorna lista de vídeos encontrados.
    """
    url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
    videos = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        feed = feedparser.parse(response.text)

        for entry in feed.entries:
            video_id = entry.get("yt_videoid", "")
            if not video_id:
                # Tentar extrair do link
                link = entry.get("link", "")
                if "v=" in link:
                    video_id = link.split("v=")[-1].split("&")[0]

            if not video_id:
                continue

            published = entry.get("published", "")
            if published:
                try:
                    pub_date = datetime.fromisoformat(
                        published.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pub_date = datetime.now(timezone.utc)
            else:
                pub_date = datetime.now(timezone.utc)

            videos.append({
                "video_id": video_id,
                "title": entry.get("title", "Sem título"),
                "channel_name": channel_name,
                "channel_id": channel_id if hasattr(entry, "yt_channelid") is False else entry.get("yt_channelid", channel_id),
                "published_at": pub_date.isoformat(),
                "link": f"https://www.youtube.com/watch?v={video_id}",
            })

        logger.info(f"[{channel_name}] Feed carregado: {len(videos)} vídeos encontrados")

    except httpx.HTTPStatusError as e:
        logger.error(f"[{channel_name}] Erro HTTP ao buscar feed: {e.response.status_code}")
    except Exception as e:
        logger.error(f"[{channel_name}] Erro ao buscar feed: {e}")

    return videos


async def check_all_feeds(max_age_days: int = 3) -> list[dict]:
    """
    Verifica todos os canais configurados e retorna vídeos novos.

    Args:
        max_age_days: Ignorar vídeos mais antigos que X dias (padrão: 3).

    Returns:
        Lista de vídeos novos que ainda não foram processados.
    """
    channels = load_channels()
    new_videos = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    for channel in channels:
        channel_id = channel.get("channel_id", "")
        channel_name = channel.get("name", "Desconhecido")
        language = channel.get("language", "en")

        # Pular canais com IDs placeholder
        if not channel_id or channel_id.startswith("PLACEHOLDER"):
            logger.warning(f"[{channel_name}] Channel ID não configurado, pulando...")
            continue

        videos = await fetch_feed(channel_id, channel_name)

        for video in videos:
            video_id = video["video_id"]

            # Verificar se já foi processado
            if video_exists(video_id):
                continue

            # Verificar idade do vídeo
            try:
                pub_date = datetime.fromisoformat(video["published_at"])
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date < cutoff_date:
                    continue
            except (ValueError, TypeError):
                pass

            # Registrar no banco
            inserted = insert_video(
                video_id=video_id,
                title=video["title"],
                channel_name=video["channel_name"],
                channel_id=video.get("channel_id", channel_id),
                published_at=video["published_at"],
                link=video["link"],
                language=language,
            )

            if inserted:
                video["language"] = language
                new_videos.append(video)
                logger.info(f"  Novo vídeo: [{channel_name}] {video['title']}")

    logger.info(f"Total de vídeos novos encontrados: {len(new_videos)}")
    return new_videos
