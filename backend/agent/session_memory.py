from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


RECENT_TURNS_LIMIT = 4
ROWS_PREVIEW_LIMIT = 3


@dataclass
class SessionTurn:
    question: str
    final_sql: Optional[str] = None
    is_valid: bool = False
    error_message: Optional[str] = None
    rows_preview: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SessionState:
    session_id: str
    summary: str = ""
    turns: list[SessionTurn] = field(default_factory=list)
    last_sql: Optional[str] = None
    last_error: Optional[str] = None


SESSION_STORE: dict[str, SessionState] = {}


def get_session_state(session_id: str) -> SessionState:
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = SessionState(session_id=session_id)
    return SESSION_STORE[session_id]


def clear_session_state(session_id: str) -> None:
    SESSION_STORE.pop(session_id, None)


def _format_rows_preview(rows: list[Any] | None) -> list[dict[str, Any]]:
    if not rows:
        return []

    preview: list[dict[str, Any]] = []
    for row in rows[:ROWS_PREVIEW_LIMIT]:
        preview.append(dict(row))
    return preview


def _refresh_summary(session: SessionState) -> None:
    recent_turns = session.turns[-RECENT_TURNS_LIMIT:]
    if not recent_turns:
        session.summary = ""
        return

    summary_parts: list[str] = []
    for turn in recent_turns:
        status = "valida" if turn.is_valid else "invalida"
        sql_text = turn.final_sql or "NULL"
        summary_parts.append(
            f"Pergunta: {turn.question} | Status: {status} | SQL: {sql_text}"
        )

    session.summary = " || ".join(summary_parts)


def register_turn(
    session_id: str,
    *,
    question: str,
    final_sql: Optional[str],
    is_valid: bool,
    error_message: Optional[str],
    rows: list[Any] | None,
) -> SessionState:
    session = get_session_state(session_id)
    turn = SessionTurn(
        question=question,
        final_sql=final_sql,
        is_valid=is_valid,
        error_message=error_message,
        rows_preview=_format_rows_preview(rows),
    )

    session.turns.append(turn)
    session.last_sql = final_sql
    session.last_error = error_message
    _refresh_summary(session)

    return session


def build_session_context(session_id: str) -> str:
    session = get_session_state(session_id)
    context_parts: list[str] = []

    if session.summary:
        context_parts.append(f"Resumo da sessao atual:\n{session.summary}")

    recent_turns = session.turns[-RECENT_TURNS_LIMIT:]
    if recent_turns:
        history_lines: list[str] = []
        for index, turn in enumerate(recent_turns, 1):
            history_lines.append(f"{index}. Pergunta: {turn.question}")
            history_lines.append(f"   SQL: {turn.final_sql or 'NULL'}")
            history_lines.append(
                f"   Status: {'valida' if turn.is_valid else 'invalida'}"
            )
            if turn.error_message:
                history_lines.append(f"   Erro: {turn.error_message}")
            if turn.rows_preview:
                history_lines.append(f"   Amostra de linhas: {turn.rows_preview}")

        context_parts.append("Historico recente da sessao:\n" + "\n".join(history_lines))

    return "\n\n".join(context_parts).strip()
