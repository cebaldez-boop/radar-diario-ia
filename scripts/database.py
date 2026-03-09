"""
Radar Diário de IA - Módulo de Banco de Dados (SQLite)
Gerencia o armazenamento de vídeos, resumos, oportunidades e relatórios.
"""

import json
import sqlite3
import os
from datetime import date
from typing import Optional


DB_PATH = os.environ.get("DB_PATH", "/app/data/radar.db")


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão com o banco de dados SQLite."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Inicializa as tabelas do banco de dados."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            published_at TEXT NOT NULL,
            link TEXT NOT NULL,
            language TEXT DEFAULT 'en',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            transcript TEXT NOT NULL,
            method TEXT DEFAULT 'gemini',
            duration_seconds REAL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        );

        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            resumo_curto TEXT,
            novas_ferramentas TEXT,
            updates_ia TEXT,
            estrategias_automacao TEXT,
            insights_mercado TEXT,
            pontos_principais TEXT,
            raw_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            empresa TEXT NOT NULL,
            oportunidade TEXT NOT NULL,
            descricao TEXT,
            tipo TEXT,
            impacto_esperado TEXT,
            dificuldade INTEGER,
            primeiro_passo TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT UNIQUE NOT NULL,
            num_videos INTEGER DEFAULT 0,
            num_opportunities INTEGER DEFAULT 0,
            report_markdown TEXT,
            report_html TEXT,
            email_sent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
        CREATE INDEX IF NOT EXISTS idx_videos_published ON videos(published_at);
        CREATE INDEX IF NOT EXISTS idx_opportunities_empresa ON opportunities(empresa);
        CREATE INDEX IF NOT EXISTS idx_opportunities_video ON opportunities(video_id);
    """)

    conn.commit()
    conn.close()


def video_exists(video_id: str) -> bool:
    """Verifica se um vídeo já foi registrado no banco."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM videos WHERE video_id = ?", (video_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def insert_video(
    video_id: str,
    title: str,
    channel_name: str,
    channel_id: str,
    published_at: str,
    link: str,
    language: str = "en",
) -> bool:
    """Insere um novo vídeo no banco. Retorna True se inserido, False se já existia."""
    if video_exists(video_id):
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO videos (video_id, title, channel_name, channel_id, published_at, link, language)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (video_id, title, channel_name, channel_id, published_at, link, language),
    )
    conn.commit()
    conn.close()
    return True


def update_video_status(video_id: str, status: str, error_message: Optional[str] = None) -> None:
    """Atualiza o status de um vídeo (pending, processing, completed, error)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE videos SET status = ?, error_message = ? WHERE video_id = ?",
        (status, error_message, video_id),
    )
    conn.commit()
    conn.close()


def save_transcript(video_id: str, transcript: str, method: str = "gemini", duration: float = 0) -> None:
    """Salva a transcrição de um vídeo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO transcripts (video_id, transcript, method, duration_seconds)
           VALUES (?, ?, ?, ?)""",
        (video_id, transcript, method, duration),
    )
    conn.commit()
    conn.close()


def save_summary(video_id: str, summary_data: dict) -> None:
    """Salva o resumo de um vídeo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO summaries
           (video_id, resumo_curto, novas_ferramentas, updates_ia,
            estrategias_automacao, insights_mercado, pontos_principais, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            video_id,
            summary_data.get("resumo_curto", ""),
            json.dumps(summary_data.get("novas_ferramentas", []), ensure_ascii=False),
            json.dumps(summary_data.get("updates_ia", []), ensure_ascii=False),
            json.dumps(summary_data.get("estrategias_automacao", []), ensure_ascii=False),
            json.dumps(summary_data.get("insights_mercado", []), ensure_ascii=False),
            json.dumps(summary_data.get("pontos_principais", []), ensure_ascii=False),
            json.dumps(summary_data, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def save_opportunities(video_id: str, opportunities_by_company: dict) -> int:
    """Salva as oportunidades geradas para um vídeo. Retorna o total salvo."""
    conn = get_connection()
    cursor = conn.cursor()
    total = 0

    for empresa, opps in opportunities_by_company.items():
        for opp in opps:
            cursor.execute(
                """INSERT INTO opportunities
                   (video_id, empresa, oportunidade, descricao, tipo,
                    impacto_esperado, dificuldade, primeiro_passo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    video_id,
                    empresa,
                    opp.get("oportunidade", ""),
                    opp.get("descricao", ""),
                    opp.get("tipo", ""),
                    opp.get("impacto_esperado", ""),
                    opp.get("dificuldade", 3),
                    opp.get("primeiro_passo", ""),
                ),
            )
            total += 1

    conn.commit()
    conn.close()
    return total


def get_pending_videos() -> list[dict]:
    """Retorna vídeos pendentes de processamento."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM videos WHERE status = 'pending' ORDER BY published_at DESC"
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_todays_videos(target_date: Optional[str] = None) -> list[dict]:
    """Retorna todos os vídeos processados hoje (ou na data especificada)."""
    if target_date is None:
        target_date = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT v.*, s.resumo_curto, s.raw_json as summary_json
           FROM videos v
           LEFT JOIN summaries s ON v.video_id = s.video_id
           WHERE date(v.created_at) = ? AND v.status = 'completed'
           ORDER BY v.published_at DESC""",
        (target_date,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_todays_opportunities(target_date: Optional[str] = None) -> list[dict]:
    """Retorna todas as oportunidades geradas hoje (ou na data especificada)."""
    if target_date is None:
        target_date = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT o.*, v.title as video_title, v.channel_name
           FROM opportunities o
           JOIN videos v ON o.video_id = v.video_id
           WHERE date(o.created_at) = ?
           ORDER BY o.empresa, o.dificuldade ASC""",
        (target_date,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def save_report(report_date: str, num_videos: int, num_opportunities: int,
                report_markdown: str, report_html: str) -> None:
    """Salva o relatório diário."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO reports
           (report_date, num_videos, num_opportunities, report_markdown, report_html)
           VALUES (?, ?, ?, ?, ?)""",
        (report_date, num_videos, num_opportunities, report_markdown, report_html),
    )
    conn.commit()
    conn.close()


def mark_report_sent(report_date: str) -> None:
    """Marca o relatório como enviado por e-mail."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE reports SET email_sent = 1 WHERE report_date = ?",
        (report_date,),
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Retorna estatísticas gerais do sistema."""
    conn = get_connection()
    cursor = conn.cursor()

    stats = {}
    cursor.execute("SELECT COUNT(*) as total FROM videos")
    stats["total_videos"] = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM videos WHERE status = 'completed'")
    stats["completed_videos"] = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM videos WHERE status = 'pending'")
    stats["pending_videos"] = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM videos WHERE status = 'error'")
    stats["error_videos"] = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM opportunities")
    stats["total_opportunities"] = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM reports")
    stats["total_reports"] = cursor.fetchone()["total"]

    conn.close()
    return stats
