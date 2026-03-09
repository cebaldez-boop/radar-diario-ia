"""
Radar Diário de IA - Módulo de Geração de Relatórios
Gera o relatório diário em Markdown e HTML.
"""

import json
import logging
import os
from datetime import date, datetime
from typing import Optional

from jinja2 import Template

from scripts.database import (
    get_todays_opportunities,
    get_todays_videos,
    save_report,
)

logger = logging.getLogger(__name__)

TEMPLATE_PATH = os.environ.get("TEMPLATE_PATH", "/app/templates/report_template.html")
REPORTS_DIR = os.environ.get("REPORTS_DIR", "/app/data/reports")


def _group_opportunities_by_company(opportunities: list[dict]) -> dict:
    """Agrupa oportunidades por empresa."""
    grouped = {
        "orbitflow": [],
        "primal_decode": [],
        "tranzit": [],
        "nexus_ai": [],
    }
    for opp in opportunities:
        empresa = opp.get("empresa", "").lower().replace(" ", "_")
        if empresa in grouped:
            grouped[empresa].append(opp)
        else:
            # Tentar mapear nomes alternativos
            mapping = {
                "orbitflow": "orbitflow",
                "primal_decode": "primal_decode",
                "primal decode": "primal_decode",
                "primaldecode": "primal_decode",
                "tranzit": "tranzit",
                "nexus_ai": "nexus_ai",
                "nexus ai": "nexus_ai",
                "nexus_ai_solutions": "nexus_ai",
                "nexus ai solutions": "nexus_ai",
            }
            mapped = mapping.get(empresa, None)
            if mapped:
                grouped[mapped].append(opp)
            else:
                # Colocar em nexus_ai como fallback
                grouped["nexus_ai"].append(opp)

    return grouped


def generate_markdown_report(
    target_date: Optional[str] = None,
    top3_actions: Optional[list[dict]] = None,
) -> str:
    """
    Gera o relatório diário em formato Markdown.

    Args:
        target_date: Data do relatório (YYYY-MM-DD). Padrão: hoje.
        top3_actions: Lista com as 3 ações prioritárias para amanhã.

    Returns:
        Relatório em Markdown.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    videos = get_todays_videos(target_date)
    opportunities = get_todays_opportunities(target_date)
    grouped_opps = _group_opportunities_by_company(opportunities)

    num_videos = len(videos)
    num_opps = len(opportunities)

    # --- Construir Markdown ---
    lines = []

    # Cabeçalho
    lines.append(f"# 📡 Radar Diário de IA — {target_date}")
    lines.append("")
    lines.append(f"**Vídeos analisados:** {num_videos}")
    lines.append(f"**Oportunidades geradas:** {num_opps}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Seção 1: Resumo das novidades
    lines.append("## 1. Resumo das Principais Novidades de IA de Hoje")
    lines.append("")

    if videos:
        for v in videos:
            title = v.get("title", "Sem título")
            channel = v.get("channel_name", "")
            link = v.get("link", "")
            resumo = v.get("resumo_curto", "Resumo não disponível")

            lines.append(f"### 🎬 [{title}]({link})")
            lines.append(f"**Canal:** {channel}")
            lines.append(f"**Resumo:** {resumo}")
            lines.append("")

            # Adicionar detalhes do resumo se disponível
            if v.get("summary_json"):
                try:
                    summary = json.loads(v["summary_json"])
                    if summary.get("novas_ferramentas"):
                        lines.append("**Ferramentas mencionadas:**")
                        for tool in summary["novas_ferramentas"]:
                            lines.append(f"  - {tool}")
                        lines.append("")
                    if summary.get("updates_ia"):
                        lines.append("**Updates de IA:**")
                        for update in summary["updates_ia"]:
                            lines.append(f"  - {update}")
                        lines.append("")
                    if summary.get("pontos_principais"):
                        lines.append("**Pontos principais:**")
                        for ponto in summary["pontos_principais"]:
                            lines.append(f"  - {ponto}")
                        lines.append("")
                except (json.JSONDecodeError, TypeError):
                    pass

            lines.append("---")
            lines.append("")
    else:
        lines.append("_Nenhum vídeo novo processado hoje._")
        lines.append("")

    # Seção 2: Oportunidades para Orbitflow
    lines.append("## 2. Oportunidades para Orbitflow")
    lines.append("")
    lines.append("_Criação de automações e soluções com IA para clientes (Upwork/EUA)_")
    lines.append("")
    _add_opportunity_table(lines, grouped_opps.get("orbitflow", []))
    lines.append("")

    # Seção 3: Oportunidades para Primal DEcode
    lines.append("## 3. Oportunidades para Primal DEcode")
    lines.append("")
    lines.append("_Canal de YouTube sobre IA — ideias de vídeos, séries, formatos, roteiros_")
    lines.append("")
    _add_opportunity_table(lines, grouped_opps.get("primal_decode", []))
    lines.append("")

    # Seção 4: Oportunidades para Tranzit
    lines.append("## 4. Oportunidades para Tranzit")
    lines.append("")
    lines.append("_Importação de produtos dos EUA para o Brasil — logística, operação, vendas_")
    lines.append("")
    _add_opportunity_table(lines, grouped_opps.get("tranzit", []))
    lines.append("")

    # Seção 5: Oportunidades para NEXUS AI Solutions
    lines.append("## 5. Oportunidades para NEXUS AI Solutions")
    lines.append("")
    lines.append("_Novos serviços e produtos de IA para oferecer_")
    lines.append("")
    _add_opportunity_table(lines, grouped_opps.get("nexus_ai", []))
    lines.append("")

    # Seção 6: Top 3 Ações
    lines.append("## 6. 🎯 Top 3 Ações Mais Importantes para Amanhã")
    lines.append("")

    if top3_actions:
        for i, action in enumerate(top3_actions, 1):
            lines.append(f"### {i}. {action.get('acao', 'Ação')}")
            lines.append(f"**Empresa:** {action.get('empresa', 'N/A')}")
            lines.append(f"**Justificativa:** {action.get('justificativa', '')}")
            lines.append(f"**Primeiro passo:** {action.get('primeiro_passo', '')}")
            lines.append("")
    else:
        lines.append("_Nenhuma ação prioritária identificada hoje._")
        lines.append("")

    # Rodapé
    lines.append("---")
    lines.append("")
    lines.append(f"_Relatório gerado automaticamente pelo Radar Diário de IA em {datetime.now().strftime('%d/%m/%Y %H:%M')}._")

    markdown = "\n".join(lines)

    # Salvar arquivo
    os.makedirs(REPORTS_DIR, exist_ok=True)
    md_path = os.path.join(REPORTS_DIR, f"relatorio_{target_date}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    logger.info(f"Relatório Markdown salvo: {md_path}")
    return markdown


def _add_opportunity_table(lines: list[str], opportunities: list[dict]) -> None:
    """Adiciona uma tabela de oportunidades ao relatório."""
    if not opportunities:
        lines.append("_Nenhuma oportunidade identificada nesta seção hoje._")
        return

    lines.append("| Oportunidade | Descrição | Tipo | Impacto Esperado | Dificuldade | Primeiro Passo |")
    lines.append("|---|---|---|---|---|---|")

    for opp in opportunities:
        nome = opp.get("oportunidade", "—")
        desc = opp.get("descricao", "—")
        tipo = opp.get("tipo", "—")
        impacto = opp.get("impacto_esperado", "—")
        diff = opp.get("dificuldade", 3)
        diff_str = "⭐" * int(diff) if isinstance(diff, (int, float)) else str(diff)
        passo = opp.get("primeiro_passo", "—")

        # Escapar pipes no Markdown
        for field in [nome, desc, tipo, impacto, passo]:
            if isinstance(field, str):
                field = field.replace("|", "\\|")

        lines.append(f"| {nome} | {desc} | {tipo} | {impacto} | {diff_str} | {passo} |")


def generate_html_report(markdown_content: str, target_date: Optional[str] = None) -> str:
    """
    Converte o relatório Markdown para HTML usando um template.

    Args:
        markdown_content: Conteúdo em Markdown.
        target_date: Data do relatório.

    Returns:
        Relatório em HTML.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    # Template HTML simples inline (caso o arquivo de template não exista)
    html_template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Radar Diário de IA — {{ date }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        h1 { color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }
        h2 { color: #16213e; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        h3 { color: #0f3460; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
            font-size: 14px;
        }
        th { background-color: #16213e; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #e8f0fe; }
        a { color: #0f3460; }
        code { background: #eee; padding: 2px 6px; border-radius: 3px; }
        hr { border: none; border-top: 1px solid #ddd; margin: 20px 0; }
        .footer { color: #888; font-size: 12px; margin-top: 40px; }
    </style>
</head>
<body>
    {{ content }}
</body>
</html>"""

    # Converter Markdown simples para HTML
    html_content = _simple_md_to_html(markdown_content)

    template = Template(html_template)
    html = template.render(date=target_date, content=html_content)

    # Salvar arquivo
    os.makedirs(REPORTS_DIR, exist_ok=True)
    html_path = os.path.join(REPORTS_DIR, f"relatorio_{target_date}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Relatório HTML salvo: {html_path}")
    return html


def _simple_md_to_html(md: str) -> str:
    """Converte Markdown simples para HTML (sem dependências externas)."""
    import re

    lines = md.split("\n")
    html_lines = []
    in_table = False
    in_table_header = False

    for line in lines:
        stripped = line.strip()

        # Linhas vazias
        if not stripped:
            if in_table:
                html_lines.append("</table>")
                in_table = False
            html_lines.append("")
            continue

        # Tabelas
        if stripped.startswith("|") and "|" in stripped[1:]:
            cells = [c.strip() for c in stripped.split("|")[1:-1]]

            # Pular linha separadora
            if all(set(c) <= set("-| ") for c in cells):
                in_table_header = False
                continue

            if not in_table:
                html_lines.append("<table>")
                in_table = True
                in_table_header = True

            tag = "th" if in_table_header else "td"
            row = "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
            html_lines.append(row)
            continue

        if in_table:
            html_lines.append("</table>")
            in_table = False

        # Headers
        if stripped.startswith("### "):
            text = stripped[4:]
            text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
            html_lines.append(f"<h3>{text}</h3>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("---"):
            html_lines.append("<hr>")
        elif stripped.startswith("- ") or stripped.startswith("  - "):
            indent = "  " if stripped.startswith("  - ") else ""
            text = stripped.lstrip(" -")
            html_lines.append(f"{indent}<li>{text}</li>")
        elif stripped.startswith("_") and stripped.endswith("_"):
            html_lines.append(f"<p><em>{stripped[1:-1]}</em></p>")
        elif stripped.startswith("**") and "**" in stripped[2:]:
            # Bold text
            text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', stripped)
            html_lines.append(f"<p>{text}</p>")
        else:
            # Links
            text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', stripped)
            text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
            html_lines.append(f"<p>{text}</p>")

    if in_table:
        html_lines.append("</table>")

    return "\n".join(html_lines)


def save_daily_report(
    target_date: Optional[str] = None,
    top3_actions: Optional[list[dict]] = None,
) -> tuple[str, str]:
    """
    Gera e salva o relatório diário completo.

    Returns:
        Tupla (markdown, html).
    """
    if target_date is None:
        target_date = date.today().isoformat()

    # Gerar Markdown
    markdown = generate_markdown_report(target_date, top3_actions)

    # Gerar HTML
    html = generate_html_report(markdown, target_date)

    # Contar vídeos e oportunidades
    videos = get_todays_videos(target_date)
    opportunities = get_todays_opportunities(target_date)

    # Salvar no banco
    save_report(
        report_date=target_date,
        num_videos=len(videos),
        num_opportunities=len(opportunities),
        report_markdown=markdown,
        report_html=html,
    )

    logger.info(
        f"Relatório diário salvo: {target_date} "
        f"({len(videos)} vídeos, {len(opportunities)} oportunidades)"
    )

    return markdown, html
