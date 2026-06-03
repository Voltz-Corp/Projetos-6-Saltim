"""
Gera o estoque historico usado pelo relatorio de criticidade.

Este arquivo existe separado do gerador de vendas porque a reconstrucao de
estoque ate 02/06/2026 serve especificamente para alimentar a serie historica
do relatorio de criticidade.
"""

from __future__ import annotations

from datetime import date, time, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import text

HISTORICAL_STOCK_END_DATE = date(2026, 6, 2)


def backfill_historical_stock_until_cutoff(
    engine, reference_date: date
) -> dict[str, Any]:
    cutoff = min(HISTORICAL_STOCK_END_DATE, reference_date)
    with engine.begin() as conn:
        latest_stock_date = conn.execute(
            text(
                "SELECT max(date(date_time)) FROM estoques WHERE date(date_time) <= :cutoff"
            ),
            {"cutoff": cutoff},
        ).scalar()
        if latest_stock_date is None:
            return {
                "status": "skipped_no_stock_history",
                "rows_created": 0,
                "target_end_date": cutoff.isoformat(),
            }
        start_date = latest_stock_date + timedelta(days=1)
        if start_date > cutoff:
            return {
                "status": "skipped_up_to_date",
                "rows_created": 0,
                "latest_stock_date": latest_stock_date.isoformat(),
                "target_end_date": cutoff.isoformat(),
            }

        last_stock = pd.read_sql_query(
            text("""
                SELECT DISTINCT ON (ingredient_id)
                    ingredient_id,
                    quantity
                FROM estoques
                WHERE date(date_time) <= :latest_stock_date
                ORDER BY ingredient_id, date_time DESC
                """),
            conn,
            params={"latest_stock_date": latest_stock_date},
        )
        current_stock = pd.read_sql_query(
            text("SELECT ingrediente AS ingredient_id, qtd FROM estoque_atual"),
            conn,
        )
        daily_usage = pd.read_sql_query(
            text("""
                SELECT
                    date(v.date_time) AS usage_date,
                    ri.ingredient_id,
                    sum(v.quantity * ri.qty) AS quantity_used
                FROM vendas v
                JOIN receitas_ingredientes ri ON ri.recipe_id = v.recipe_id
                WHERE date(v.date_time) BETWEEN :start_date AND :cutoff
                GROUP BY 1, 2
                """),
            conn,
            params={"start_date": start_date, "cutoff": cutoff},
        )

    if last_stock.empty:
        return {
            "status": "skipped_missing_stock_inputs",
            "rows_created": 0,
            "target_start_date": start_date.isoformat(),
            "target_end_date": cutoff.isoformat(),
        }

    start_by_ingredient = {
        str(row.ingredient_id): max(0.0, float(row.quantity or 0.0))
        for row in last_stock.itertuples(index=False)
    }
    target_by_ingredient = {
        str(row.ingredient_id): max(0.0, float(row.qtd or 0.0))
        for row in current_stock.itertuples(index=False)
    }
    usage_by_day_ingredient = {
        (pd.Timestamp(row.usage_date).date(), str(row.ingredient_id)): max(
            0.0, float(row.quantity_used or 0.0)
        )
        for row in daily_usage.itertuples(index=False)
    }

    dates = [item.date() for item in pd.date_range(start_date, cutoff, freq="D")]
    n_days = max(1, len(dates))
    records: list[dict[str, Any]] = []
    for ingredient_id, start_qty in start_by_ingredient.items():
        target_qty = target_by_ingredient.get(ingredient_id, start_qty)
        total_usage = sum(
            usage_by_day_ingredient.get((current_date, ingredient_id), 0.0)
            for current_date in dates
        )
        raw_end_qty = max(0.0, start_qty - total_usage)
        adjustment = target_qty - raw_end_qty
        cumulative_usage = 0.0
        for idx, current_date in enumerate(dates, start=1):
            cumulative_usage += usage_by_day_ingredient.get(
                (current_date, ingredient_id), 0.0
            )
            progressive_adjustment = adjustment * (idx / n_days)
            quantity = max(0.0, start_qty - cumulative_usage + progressive_adjustment)
            records.append(
                {
                    "id": "",
                    "date_time": pd.Timestamp.combine(
                        current_date, time(23, 59, 0)
                    ).to_pydatetime(),
                    "ingredient_id": ingredient_id,
                    "quantity": round(quantity, 4),
                }
            )

    if not records:
        return {
            "status": "skipped_no_stock_records",
            "rows_created": 0,
            "target_start_date": start_date.isoformat(),
            "target_end_date": cutoff.isoformat(),
        }

    with engine.begin() as conn:
        conn.execute(
            text("""
                DELETE FROM estoques
                WHERE date(date_time) BETWEEN :start_date AND :cutoff
                """),
            {"start_date": start_date, "cutoff": cutoff},
        )
        next_id = int(
            conn.execute(
                text("""
                    SELECT COALESCE(max(CAST(substring(id FROM 4) AS BIGINT)), 0) + 1
                    FROM estoques
                    WHERE id ~ '^EST[0-9]{9}$'
                    """)
            ).scalar()
            or 1
        )
        for offset, record in enumerate(records):
            record["id"] = f"EST{next_id + offset:09d}"
        conn.execute(
            text("""
                INSERT INTO estoques (id, date_time, ingredient_id, quantity)
                VALUES (:id, :date_time, :ingredient_id, :quantity)
                ON CONFLICT (id) DO NOTHING
                """),
            records,
        )

    return {
        "status": "created",
        "rows_created": len(records),
        "ingredients": len(start_by_ingredient),
        "created_days": len(dates),
        "target_start_date": start_date.isoformat(),
        "target_end_date": cutoff.isoformat(),
    }
