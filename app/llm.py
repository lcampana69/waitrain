"""Simple, local stubs for LLM-driven behaviors."""
from __future__ import annotations

from typing import Dict, List, Tuple

DEFAULT_USER_PROMPT = (
    "Genera una consulta SQL segura basándote en el esquema proporcionado y la pregunta."
)


def build_sql_for_question(question: str, schema: Dict[str, List[Dict[str, str]]], system_prompt: str) -> str:
    """Derive a SQL statement from a natural language question.

    In a real deployment this function would call an LLM. Here we keep the
    logic deterministic and transparent for local development.
    """
    # Extremely conservative demo: select all tables mentioned in the question
    lowered = question.lower()
    for table_name in schema:
        if table_name.lower() in lowered:
            return f"SELECT * FROM {table_name} LIMIT 50;"

    # Fallback to list available tables if nothing matches.
    tables = ", ".join(f"'{name}'" for name in schema.keys())
    return (
        "-- No direct table match, enumerating tables\n"
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name IN ("
        f"{tables}) LIMIT 50;"
    )


def render_answer(columns: List[str], rows: List[Tuple]) -> Dict[str, object]:
    """Return a simple render-friendly payload."""
    return {
        "summary": f"{len(rows)} filas devueltas.",
        "columns": columns,
        "rows": [list(row) for row in rows],
    }
