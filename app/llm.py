"""LLM helpers backed by OpenAI's ChatGPT models."""
from __future__ import annotations

from typing import Dict, List, Tuple

from openai import OpenAI

DEFAULT_USER_PROMPT = (
    "Genera una consulta SQL segura basándote en el esquema proporcionado y la pregunta."
)


def get_openai_client(api_key: str) -> OpenAI:
    """Instantiate an OpenAI client."""

    return OpenAI(api_key=api_key)


def _format_schema(schema: Dict[str, List[Dict[str, str]]]) -> str:
    sections: List[str] = []
    for table, columns in schema.items():
        sections.append(f"Tabla {table}:")
        for column in columns:
            sections.append(
                f"- {column.get('column_name')} ({column.get('data_type')})"
            )
    return "\n".join(sections)


def build_sql_for_question(
    question: str,
    schema: Dict[str, List[Dict[str, str]]],
    system_prompt: str,
    client: OpenAI,
    model: str,
) -> str:
    """Use ChatGPT to transform a natural-language question into SQL."""

    schema_prompt = _format_schema(schema)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    f"{system_prompt}\n"
                    "Responde solo con la consulta SQL final, sin formato adicional ni "
                    "comentarios. Usa únicamente tablas y columnas del esquema."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Esquema detectado:\n{schema_prompt}\n\n"
                    f"Pregunta del usuario: {question}\n"
                    "Añade LIMIT 50 a las consultas potencialmente grandes."
                ),
            },
        ],
    )

    return response.choices[0].message.content.strip()


def render_answer(
    columns: List[str], rows: List[Tuple], client: OpenAI, model: str
) -> Dict[str, object]:
    """Ask the LLM for a human-friendly summary of query results."""

    preview_rows = [dict(zip(columns, row)) for row in rows[:5]]
    response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": "Resume en español los resultados devueltos por la consulta SQL.",
            },
            {
                "role": "user",
                "content": (
                    "Devuelve un párrafo corto y claro para mostrar al usuario. "
                    "No inventes datos que no estén en la muestra.\n"
                    f"Columnas: {columns}\nEjemplo de filas: {preview_rows}"
                ),
            },
        ],
    )

    return {
        "summary": response.choices[0].message.content.strip(),
        "columns": columns,
        "rows": [list(row) for row in rows],
    }
