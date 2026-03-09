"""
Radar Diário de IA - Módulo de Download de Áudio
Baixa o áudio de vídeos do YouTube usando yt-dlp.
"""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)

AUDIO_DIR = os.environ.get("AUDIO_DIR", "/app/data/audio")


def ensure_audio_dir() -> None:
    """Garante que o diretório de áudio existe."""
    os.makedirs(AUDIO_DIR, exist_ok=True)


def download_audio(video_id: str, max_duration_minutes: int = 120) -> str:
    """
    Baixa o áudio de um vídeo do YouTube.

    Args:
        video_id: ID do vídeo no YouTube.
        max_duration_minutes: Duração máxima em minutos (pular vídeos muito longos).

    Returns:
        Caminho do arquivo de áudio baixado.

    Raises:
        RuntimeError: Se o download falhar.
    """
    ensure_audio_dir()
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = os.path.join(AUDIO_DIR, f"{video_id}.mp3")

    # Se já existe, retornar o caminho
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        logger.info(f"Áudio já existe: {output_path}")
        return output_path

    logger.info(f"Baixando áudio: {video_id}")

    try:
        # Primeiro, verificar duração
        duration_cmd = [
            "yt-dlp",
            "--print", "duration",
            "--no-download",
            url,
        ]
        result = subprocess.run(
            duration_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                duration_seconds = float(result.stdout.strip())
                if duration_seconds > max_duration_minutes * 60:
                    raise RuntimeError(
                        f"Vídeo muito longo ({duration_seconds / 60:.0f} min). "
                        f"Limite: {max_duration_minutes} min."
                    )
            except ValueError:
                pass  # Não conseguiu parsear, continuar com download

        # Baixar áudio
        download_cmd = [
            "yt-dlp",
            "-x",                          # Extrair apenas áudio
            "--audio-format", "mp3",       # Formato MP3
            "--audio-quality", "5",        # Qualidade média (menor arquivo)
            "-o", output_path,             # Caminho de saída
            "--no-playlist",               # Não baixar playlists
            "--no-overwrites",             # Não sobrescrever
            "--socket-timeout", "30",      # Timeout de conexão
            "--retries", "3",              # Tentativas de retry
            url,
        ]

        result = subprocess.run(
            download_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutos de timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Erro desconhecido"
            raise RuntimeError(f"yt-dlp falhou: {error_msg[:500]}")

        # Verificar se o arquivo foi criado
        # yt-dlp pode adicionar extensão adicional
        possible_paths = [
            output_path,
            output_path + ".mp3",
            os.path.join(AUDIO_DIR, f"{video_id}.mp3.mp3"),
        ]

        for path in possible_paths:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                if path != output_path:
                    os.rename(path, output_path)
                logger.info(f"Áudio baixado com sucesso: {output_path}")
                return output_path

        raise RuntimeError("Arquivo de áudio não encontrado após download")

    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout ao baixar áudio (>10 min)")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Erro ao baixar áudio: {e}")


def cleanup_audio(video_id: str) -> None:
    """Remove o arquivo de áudio de um vídeo (para economizar espaço)."""
    audio_path = os.path.join(AUDIO_DIR, f"{video_id}.mp3")
    if os.path.exists(audio_path):
        os.remove(audio_path)
        logger.info(f"Áudio removido: {audio_path}")


def get_audio_size_mb(video_id: str) -> float:
    """Retorna o tamanho do arquivo de áudio em MB."""
    audio_path = os.path.join(AUDIO_DIR, f"{video_id}.mp3")
    if os.path.exists(audio_path):
        return os.path.getsize(audio_path) / (1024 * 1024)
    return 0.0
