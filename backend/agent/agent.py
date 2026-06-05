from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .context_enricher import build_context_payload
from .database import execute_query
from .prompt import SYSTEM_PROMPT
from .session_memory import (
    build_session_context,
    clear_session_state,
    register_turn,
)
from .utils import get_tabelas_validas, validar_sql

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - dependency is declared in requirements
    genai = None
    types = None


load_dotenv()

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"


class SaltimAgentContext(BaseModel):
    question: str
    candidate_sql: Optional[str] = None
    final_sql: Optional[str] = None
    is_valid: bool = False
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    rows: list[dict[str, Any]] | None = Field(default=None)


def _configuration_error(question: str) -> SaltimAgentContext:
    message = (
        "GOOGLE_API_KEY nao esta configurada. Configure essa variavel para "
        "usar o agente Text-to-SQL do Saltim."
    )
    if genai is None or types is None:
        message = (
            "Dependencia google-genai nao esta instalada. Instale as "
            "dependencias do backend antes de usar o agente."
        )

    return SaltimAgentContext(
        question=question,
        is_valid=False,
        error_type="configuracao_indisponivel",
        error_message=message,
    )


def _client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def _parse_response(parsed: Any, question: str) -> SaltimAgentContext:
    if isinstance(parsed, SaltimAgentContext):
        return parsed
    if isinstance(parsed, dict):
        return SaltimAgentContext(**parsed)
    return SaltimAgentContext(
        question=question,
        is_valid=False,
        error_type="erro_execucao",
        error_message="O modelo nao retornou um JSON valido para o agente.",
    )


def perguntar(question: str, session_id: str = "default") -> dict:
    client = _client()
    if client is None or types is None:
        ctx = _configuration_error(question)
        register_turn(
            session_id,
            question=question,
            final_sql=ctx.final_sql,
            is_valid=ctx.is_valid,
            error_message=ctx.error_message,
            rows=ctx.rows,
        )
        return ctx.model_dump()

    session_context = build_session_context(session_id)
    enriched_payload = build_context_payload(question)
    prompt_parts: list[str] = []

    if session_context:
        prompt_parts.append(session_context)

    if enriched_payload.get("context"):
        prompt_parts.append(
            "Contexto de amostras relevantes:\n"
            f"Plano: {enriched_payload.get('targets', [])}\n"
            f"Amostras:\n{enriched_payload['context']}"
        )

    prompt_parts.append(f"Pergunta atual do usuario:\n{question}")

    try:
        response = client.models.generate_content(
            model=os.getenv("GOOGLE_MODEL", DEFAULT_MODEL),
            contents="\n\n".join(prompt_parts),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=SaltimAgentContext,
                temperature=0.1,
            ),
        )
        ctx = _parse_response(response.parsed, question)
    except Exception as exc:
        ctx = SaltimAgentContext(
            question=question,
            is_valid=False,
            error_type="erro_execucao",
            error_message=f"Erro ao chamar o modelo: {exc}",
        )

    if ctx.is_valid and ctx.final_sql:
        try:
            ctx.final_sql = validar_sql(ctx.final_sql, get_tabelas_validas())
            ctx.rows = execute_query(ctx.final_sql)
        except Exception as exc:
            ctx.is_valid = False
            ctx.rows = None
            ctx.error_type = "erro_execucao"
            ctx.error_message = f"Erro ao validar ou executar SQL: {exc}"

    register_turn(
        session_id,
        question=question,
        final_sql=ctx.final_sql,
        is_valid=ctx.is_valid,
        error_message=ctx.error_message,
        rows=ctx.rows,
    )

    return ctx.model_dump()


def call_agent(question: str, session_id: str = "default") -> str:
    try:
        ctx = perguntar(question, session_id=session_id)
    except Exception as exc:
        return f"ERROR calling agent: {exc}"

    final_sql = ctx.get("final_sql")
    is_valid = ctx.get("is_valid")
    error = ctx.get("error_message")
    rows = ctx.get("rows")

    if final_sql:
        out = ["```sql", final_sql, "```"]
        if rows:
            out.append("Amostra de resultados:")
            for row in rows[:5]:
                out.append(str(tuple(row.values())))
        return "\n".join(out)

    if not is_valid and error:
        return error

    return str(ctx)


if __name__ == "__main__":
    clear_session_state("default")
    result = perguntar(
        "Quais ingredientes estao com estoque zerado?",
        session_id="default",
    )
    print(result.get("error_message") or result)
