"""
Radar Diário de IA - Módulo de Resumo e Oportunidades
Usa Gemini para gerar resumos e oportunidades de negócio.
"""

import json
import logging
import os

import google.generativeai as genai

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PROMPTS_PATH = os.environ.get("PROMPTS_PATH", "/app/config/prompts.json")


def _load_prompts() -> dict:
    """Carrega os prompts do arquivo de configuração."""
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _call_gemini(prompt: str, temperature: float = 0.3) -> str:
    """Faz uma chamada à API do Gemini."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não configurada")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )

    return response.text.strip()


def _parse_json_response(text: str) -> dict:
    """Tenta parsear uma resposta JSON, mesmo com formatação imperfeita."""
    # Remover blocos de código markdown
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Tentar encontrar o JSON no texto
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        logger.error(f"Não foi possível parsear JSON: {text[:200]}...")
        return {}


def generate_summary(
    title: str,
    channel: str,
    date: str,
    transcript: str,
    max_transcript_chars: int = 15000,
) -> dict:
    """
    Gera um resumo estruturado de um vídeo.

    Args:
        title: Título do vídeo.
        channel: Nome do canal.
        date: Data de publicação.
        transcript: Texto da transcrição.
        max_transcript_chars: Limite de caracteres da transcrição (para economizar tokens).

    Returns:
        Dicionário com o resumo estruturado.
    """
    prompts = _load_prompts()

    # Truncar transcrição se necessário
    if len(transcript) > max_transcript_chars:
        transcript = transcript[:max_transcript_chars] + "\n\n[... transcrição truncada por limite de tamanho ...]"

    prompt = prompts["summary_prompt"].format(
        title=title,
        channel=channel,
        date=date,
        transcript=transcript,
    )

    logger.info(f"Gerando resumo para: {title}")
    response_text = _call_gemini(prompt, temperature=0.2)
    summary = _parse_json_response(response_text)

    if not summary:
        # Retornar estrutura padrão vazia
        summary = {
            "resumo_curto": f"Erro ao gerar resumo para: {title}",
            "novas_ferramentas": [],
            "updates_ia": [],
            "estrategias_automacao": [],
            "insights_mercado": [],
            "pontos_principais": [],
        }

    return summary


def generate_opportunities(
    title: str,
    channel: str,
    summary: dict,
) -> dict:
    """
    Gera oportunidades de negócio para cada empresa.

    Args:
        title: Título do vídeo.
        channel: Nome do canal.
        summary: Dicionário com o resumo do vídeo.

    Returns:
        Dicionário com oportunidades por empresa.
    """
    prompts = _load_prompts()

    prompt = prompts["opportunities_prompt"].format(
        title=title,
        channel=channel,
        summary=summary.get("resumo_curto", ""),
        tools=", ".join(summary.get("novas_ferramentas", [])),
        updates=", ".join(summary.get("updates_ia", [])),
        strategies=", ".join(summary.get("estrategias_automacao", [])),
        insights=", ".join(summary.get("insights_mercado", [])),
    )

    logger.info(f"Gerando oportunidades para: {title}")
    response_text = _call_gemini(prompt, temperature=0.4)
    opportunities = _parse_json_response(response_text)

    # Validar estrutura
    expected_keys = ["orbitflow", "primal_decode", "tranzit", "nexus_ai"]
    for key in expected_keys:
        if key not in opportunities:
            opportunities[key] = []
        # Garantir que cada oportunidade tem os campos necessários
        for opp in opportunities[key]:
            opp.setdefault("oportunidade", "Oportunidade genérica")
            opp.setdefault("descricao", "")
            opp.setdefault("tipo", "melhoria interna")
            opp.setdefault("impacto_esperado", "A avaliar")
            opp.setdefault("dificuldade", 3)
            opp.setdefault("primeiro_passo", "Pesquisar mais sobre o tema")

    return opportunities


def generate_top3_actions(all_opportunities: list[dict]) -> list[dict]:
    """
    Seleciona as top 3 ações mais importantes para amanhã.

    Args:
        all_opportunities: Lista de todas as oportunidades geradas hoje.

    Returns:
        Lista com as 3 ações prioritárias.
    """
    if not all_opportunities:
        return [{
            "acao": "Revisar configuração do Radar",
            "empresa": "Todas",
            "justificativa": "Nenhuma oportunidade gerada hoje",
            "primeiro_passo": "Verificar se os canais estão configurados corretamente",
        }]

    prompts = _load_prompts()

    # Formatar oportunidades para o prompt
    opp_text = json.dumps(all_opportunities, ensure_ascii=False, indent=2)

    # Limitar tamanho
    if len(opp_text) > 10000:
        opp_text = opp_text[:10000] + "\n...]"

    prompt = prompts["top3_prompt"].format(opportunities=opp_text)

    logger.info("Gerando Top 3 ações para amanhã")
    response_text = _call_gemini(prompt, temperature=0.3)
    result = _parse_json_response(response_text)

    top3 = result.get("top3", [])
    if not top3:
        # Selecionar manualmente as de menor dificuldade
        sorted_opps = sorted(all_opportunities, key=lambda x: x.get("dificuldade", 5))
        top3 = []
        for opp in sorted_opps[:3]:
            top3.append({
                "acao": opp.get("oportunidade", "Ação"),
                "empresa": opp.get("empresa", "N/A"),
                "justificativa": opp.get("impacto_esperado", "Alto impacto"),
                "primeiro_passo": opp.get("primeiro_passo", "Avaliar"),
            })

    return top3


def transcribe_and_summarize_combined(
    audio_path: str,
    title: str,
    channel: str,
    date: str,
    language: str = "en",
    max_transcript_chars: int = 15000,
) -> tuple[str, dict]:
    """
    Combina transcrição e resumo em uma única chamada do Gemini
    para vídeos curtos (economiza chamadas de API).

    Para vídeos longos, a transcrição é feita separadamente.

    Args:
        audio_path: Caminho do arquivo de áudio.
        title: Título do vídeo.
        channel: Nome do canal.
        date: Data de publicação.
        language: Idioma do áudio.
        max_transcript_chars: Limite de transcrição.

    Returns:
        Tupla (transcrição, resumo).
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não configurada")

    genai.configure(api_key=GEMINI_API_KEY)

    # Verificar tamanho do arquivo (se > 20MB, fazer separado)
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb > 20:
        logger.info(f"Arquivo grande ({file_size_mb:.1f}MB), processando separadamente")
        return None, None  # Sinalizar para processar separadamente

    # Upload do áudio
    audio_file = genai.upload_file(audio_path)

    import time
    while audio_file.state.name == "PROCESSING":
        time.sleep(5)
        audio_file = genai.get_file(audio_file.name)

    if audio_file.state.name == "FAILED":
        raise RuntimeError("Falha no upload do áudio")

    lang_name = "português brasileiro" if language == "pt" else "inglês"

    prompt = f"""Analise o áudio deste vídeo do YouTube e retorne um JSON com dois campos:

INFORMAÇÕES DO VÍDEO:
- Título: {title}
- Canal: {channel}
- Data: {date}
- Idioma do áudio: {lang_name}

Retorne o seguinte JSON:
{{
  "transcricao": "transcrição completa do áudio (em {lang_name})",
  "resumo": {{
    "resumo_curto": "Uma frase resumindo o conteúdo principal (em português do Brasil)",
    "novas_ferramentas": ["lista de novas ferramentas de IA mencionadas"],
    "updates_ia": ["lista de atualizações/novidades de IA"],
    "estrategias_automacao": ["estratégias ou fluxos de automação mencionados"],
    "insights_mercado": ["insights importantes de mercado"],
    "pontos_principais": ["bullet 1", "bullet 2", "bullet 3"]
  }}
}}

IMPORTANTE:
- A transcrição deve ser no idioma original do áudio.
- O resumo deve ser SEMPRE em português do Brasil.
- Se o vídeo não mencionar alguma categoria, retorne lista vazia [].
- Retorne APENAS o JSON válido."""

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        [audio_file, prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=8192,
            response_mime_type="application/json",
        ),
    )

    # Limpar arquivo
    try:
        genai.delete_file(audio_file.name)
    except Exception:
        pass

    result = _parse_json_response(response.text)
    transcript = result.get("transcricao", "")
    summary = result.get("resumo", {})

    return transcript, summary
