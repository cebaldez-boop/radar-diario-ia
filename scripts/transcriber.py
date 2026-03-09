"""
Radar Diário de IA - Módulo de Transcrição
Transcreve áudio de vídeos usando Gemini API ou Whisper local.
"""

import logging
import os
import time

import google.generativeai as genai

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")


def transcribe_with_gemini(audio_path: str, language: str = "en") -> str:
    """
    Transcreve áudio usando a API do Gemini.
    Envia o arquivo de áudio e pede transcrição.

    Args:
        audio_path: Caminho do arquivo de áudio.
        language: Idioma do áudio ('en' ou 'pt').

    Returns:
        Texto da transcrição.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não configurada")

    genai.configure(api_key=GEMINI_API_KEY)

    logger.info(f"Transcrevendo com Gemini: {audio_path}")

    # Upload do arquivo de áudio
    audio_file = genai.upload_file(audio_path)

    # Aguardar processamento
    while audio_file.state.name == "PROCESSING":
        logger.info("  Aguardando processamento do áudio...")
        time.sleep(5)
        audio_file = genai.get_file(audio_file.name)

    if audio_file.state.name == "FAILED":
        raise RuntimeError(f"Falha no upload do áudio: {audio_file.state.name}")

    # Criar prompt de transcrição
    lang_name = "português brasileiro" if language == "pt" else "inglês"
    prompt = (
        f"Transcreva o áudio completo deste arquivo. O áudio está em {lang_name}. "
        f"Retorne APENAS a transcrição, sem comentários, timestamps ou formatação especial. "
        f"Se houver partes inaudíveis, indique com [inaudível]."
    )

    # Chamar o modelo
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        [audio_file, prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
        ),
    )

    # Limpar arquivo do servidor
    try:
        genai.delete_file(audio_file.name)
    except Exception:
        pass  # Não é crítico

    transcript = response.text.strip()
    logger.info(f"Transcrição concluída: {len(transcript)} caracteres")
    return transcript


def transcribe_with_whisper(audio_path: str, language: str = "en") -> str:
    """
    Transcreve áudio usando faster-whisper (local).
    Mais lento mas 100% gratuito.

    Args:
        audio_path: Caminho do arquivo de áudio.
        language: Idioma do áudio ('en' ou 'pt').

    Returns:
        Texto da transcrição.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper não instalado. "
            "Instale com: pip install faster-whisper"
        )

    logger.info(f"Transcrevendo com Whisper ({WHISPER_MODEL}): {audio_path}")

    model = WhisperModel(
        WHISPER_MODEL,
        device="cpu",
        compute_type="int8",
    )

    lang_code = "pt" if language == "pt" else "en"
    segments, info = model.transcribe(
        audio_path,
        language=lang_code,
        beam_size=5,
        vad_filter=True,
    )

    transcript_parts = []
    for segment in segments:
        transcript_parts.append(segment.text.strip())

    transcript = " ".join(transcript_parts)
    logger.info(
        f"Transcrição concluída: {len(transcript)} caracteres "
        f"(duração: {info.duration:.0f}s)"
    )
    return transcript


def transcribe(audio_path: str, language: str = "en", method: str = "gemini") -> tuple[str, str]:
    """
    Transcreve um arquivo de áudio usando o método especificado.

    Args:
        audio_path: Caminho do arquivo de áudio.
        language: Idioma do áudio.
        method: 'gemini' ou 'whisper'.

    Returns:
        Tupla (transcrição, método_usado).
    """
    if method == "gemini" and GEMINI_API_KEY:
        try:
            transcript = transcribe_with_gemini(audio_path, language)
            return transcript, "gemini"
        except Exception as e:
            logger.warning(f"Falha na transcrição com Gemini: {e}. Tentando Whisper...")
            # Fallback para Whisper
            try:
                transcript = transcribe_with_whisper(audio_path, language)
                return transcript, "whisper"
            except Exception as e2:
                raise RuntimeError(f"Falha em ambos os métodos: Gemini={e}, Whisper={e2}")

    elif method == "whisper":
        transcript = transcribe_with_whisper(audio_path, language)
        return transcript, "whisper"

    else:
        raise RuntimeError(
            "Nenhum método de transcrição disponível. "
            "Configure GEMINI_API_KEY ou instale faster-whisper."
        )
