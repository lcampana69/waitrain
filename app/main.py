"""FastAPI application providing NL-to-SQL querying."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Settings, load_settings
from .db import get_engine, get_or_extract_schema, run_sql_query
from .llm import build_sql_for_question, get_openai_client, render_answer

logger = logging.getLogger(__name__)

app = FastAPI(title="Waitrain NL-SQL")
_STATIC_INDEX = Path(__file__).resolve().parent / "static" / "index.html"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    texto: str = Field(..., description="Pregunta en lenguaje natural")


class QueryResult(BaseModel):
    sql: str
    rendering: Dict[str, object]


class DiagnosticStatus(BaseModel):
    name: str
    status: str
    detail: str | None = None


class Diagnostics(BaseModel):
    ok: bool
    checks: list[DiagnosticStatus]


def get_context(config_path: str | None = None):
    settings = load_settings(config_path)
    engine = get_engine(settings.dsn)
    schema = get_or_extract_schema(engine, settings.schema_cache_path)
    return settings, engine, schema


def _http_error(exc: Exception, *, context: str) -> HTTPException:
    """Normalize exceptions into HTTP errors with structured details."""

    if isinstance(exc, FileNotFoundError):
        status = 500
        kind = "config_missing"
    elif isinstance(exc, ValueError):
        status = 400
        kind = "config_invalid"
    elif isinstance(exc, SQLAlchemyError):
        status = 500
        kind = "db_error"
    else:
        status = 500
        kind = "unexpected"

    return HTTPException(
        status_code=status,
        detail={"kind": kind, "context": context, "message": str(exc)},
    )


@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        return _STATIC_INDEX.read_text(encoding="utf-8")
    except FileNotFoundError as exc:  # pragma: no cover - runtime safety
        logger.exception("Static index not found")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/schema")
async def schema(settings: Settings = Depends(load_settings)):
    engine = get_engine(settings.dsn)
    schema_map = get_or_extract_schema(engine, settings.schema_cache_path)
    return schema_map


@app.get("/diagnostics", response_model=Diagnostics)
async def diagnostics():
    checks: list[DiagnosticStatus] = []

    try:
        settings = load_settings()
        checks.append(DiagnosticStatus(name="config", status="ok"))
    except Exception as exc:  # pragma: no cover - runtime safety
        checks.append(
            DiagnosticStatus(
                name="config", status="error", detail=str(exc)
            )
        )
        return Diagnostics(ok=False, checks=checks)

    try:
        engine = get_engine(settings.dsn)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks.append(DiagnosticStatus(name="database", status="ok"))
    except Exception as exc:  # pragma: no cover - runtime safety
        checks.append(
            DiagnosticStatus(
                name="database", status="error", detail=str(exc)
            )
        )
        return Diagnostics(ok=False, checks=checks)

    try:
        schema_map = get_or_extract_schema(engine, settings.schema_cache_path)
        checks.append(DiagnosticStatus(name="schema_cache", status="ok"))
        cache_detail = f"Tablas detectadas: {len(schema_map)}"
        checks[-1].detail = cache_detail
    except Exception as exc:  # pragma: no cover - runtime safety
        checks.append(
            DiagnosticStatus(
                name="schema_cache", status="error", detail=str(exc)
            )
        )
        return Diagnostics(ok=False, checks=checks)

    return Diagnostics(ok=True, checks=checks)


@app.post("/question", response_model=QueryResult)
async def ask(
    payload: Question,
    settings: Settings = Depends(load_settings),
):
    try:
        engine = get_engine(settings.dsn)
        schema_map = get_or_extract_schema(engine, settings.schema_cache_path)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.exception("Error initializing database context")
        raise _http_error(exc, context="init") from exc

    client = get_openai_client(settings.llm_api_key)
    sql = build_sql_for_question(
        payload.texto, schema_map, settings.system_prompt, client, settings.llm_model
    )

    try:
        columns, rows = run_sql_query(engine, sql)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.exception("Error executing generated SQL")
        raise _http_error(exc, context="execution") from exc

    rendering = render_answer(columns, rows, client, settings.llm_model)

    return QueryResult(sql=sql, rendering=rendering)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
