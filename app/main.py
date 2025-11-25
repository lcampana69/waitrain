"""FastAPI application providing NL-to-SQL querying."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

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


def get_context(config_path: str | None = None):
    settings = load_settings(config_path)
    engine = get_engine(settings.dsn)
    schema = get_or_extract_schema(engine, settings.schema_cache_path)
    return settings, engine, schema


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
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    client = get_openai_client(settings.llm_api_key)
    sql = build_sql_for_question(
        payload.texto, schema_map, settings.system_prompt, client, settings.llm_model
    )

    try:
        columns, rows = run_sql_query(engine, sql)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.exception("Error executing generated SQL")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    rendering = render_answer(columns, rows, client, settings.llm_model)

    return QueryResult(sql=sql, rendering=rendering)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
