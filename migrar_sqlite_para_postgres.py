#!/usr/bin/env python3
"""
Migra dados de um SQLite local para um PostgreSQL remoto/local.

Uso (PowerShell):
    $env:TARGET_DATABASE_URL='postgresql+psycopg2://user:senha@host:5432/db'
    .\\.venv\\Scripts\\python.exe migrar_sqlite_para_postgres.py --source barbearia.db

Opcoes:
  --source PATH        Arquivo SQLite de origem (padrao: barbearia.db)
  --target-url URL     URL PostgreSQL de destino (ou use TARGET_DATABASE_URL)
  --no-truncate        Nao limpa tabelas de destino antes de importar
  --batch-size N       Tamanho do lote de insert (padrao: 1000)
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.engine import Engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migracao SQLite -> PostgreSQL")
    parser.add_argument("--source", default="barbearia.db", help="Caminho do SQLite de origem")
    parser.add_argument("--target-url", default=os.getenv("TARGET_DATABASE_URL", ""), help="URL PostgreSQL de destino")
    parser.add_argument("--no-truncate", action="store_true", help="Nao limpa tabelas antes de importar")
    parser.add_argument("--batch-size", type=int, default=1000, help="Qtd de registros por lote")
    return parser.parse_args()


def ensure_postgres_url(url: str) -> None:
    if not url:
        raise SystemExit(
            "TARGET_DATABASE_URL nao informado. Use --target-url ou variavel de ambiente TARGET_DATABASE_URL."
        )
    lower = url.lower()
    if "postgresql" not in lower:
        raise SystemExit("A URL de destino precisa ser PostgreSQL (postgresql:// ou postgresql+psycopg2://).")


def get_sqlite_tables(sqlite_engine: Engine) -> list[str]:
    insp = inspect(sqlite_engine)
    return [t for t in insp.get_table_names() if t != "sqlite_sequence"]


def get_common_columns(sqlite_engine: Engine, pg_engine: Engine, table_name: str) -> list[str]:
    sqlite_cols = {c["name"] for c in inspect(sqlite_engine).get_columns(table_name)}
    pg_cols = [c["name"] for c in inspect(pg_engine).get_columns(table_name)]
    return [c for c in pg_cols if c in sqlite_cols]


def truncate_target_tables(pg_engine: Engine, tables: list[str]) -> None:
    if not tables:
        return
    quoted = ", ".join(f'"{t}"' for t in tables)
    sql = text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
    with pg_engine.begin() as conn:
        conn.execute(sql)


def fetch_sqlite_rows(sqlite_engine: Engine, table_name: str, columns: list[str]) -> list[dict[str, Any]]:
    if not columns:
        return []
    cols_sql = ", ".join(f'"{c}"' for c in columns)
    query = text(f"SELECT {cols_sql} FROM \"{table_name}\"")
    with sqlite_engine.connect() as conn:
        result = conn.execute(query)
        return [dict(row._mapping) for row in result]


def insert_rows_in_batches(
    pg_engine: Engine,
    table_name: str,
    rows: list[dict[str, Any]],
    batch_size: int,
) -> int:
    if not rows:
        return 0

    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=pg_engine)

    inserted = 0
    with pg_engine.begin() as conn:
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            conn.execute(table.insert(), batch)
            inserted += len(batch)

    return inserted


def reset_sequence_if_needed(pg_engine: Engine, table_name: str) -> None:
    # Ajusta sequence da coluna id para evitar conflito no proximo insert sem id.
    sql = text(
        """
        SELECT pg_get_serial_sequence(:tbl, 'id') AS seq_name
        """
    )

    with pg_engine.begin() as conn:
        seq_name = conn.execute(sql, {"tbl": table_name}).scalar()
        if not seq_name:
            return
        conn.execute(
            text(
                """
                SELECT setval(
                    :seq,
                    COALESCE((SELECT MAX(id) FROM """ + f'"{table_name}"' + """), 1),
                    (SELECT COUNT(*) > 0 FROM """ + f'"{table_name}"' + """)
                )
                """
            ),
            {"seq": seq_name},
        )


def main() -> None:
    args = parse_args()
    ensure_postgres_url(args.target_url)

    sqlite_url = f"sqlite:///{args.source}"
    sqlite_engine = create_engine(sqlite_url)
    pg_engine = create_engine(args.target_url)

    sqlite_tables = get_sqlite_tables(sqlite_engine)
    pg_tables = set(inspect(pg_engine).get_table_names())

    tables_to_copy = [t for t in sqlite_tables if t in pg_tables]
    missing_in_pg = [t for t in sqlite_tables if t not in pg_tables]

    print("=" * 72)
    print("MIGRACAO SQLITE -> POSTGRESQL")
    print("=" * 72)
    print(f"SQLite origem: {args.source}")
    print(f"Tabelas no SQLite: {len(sqlite_tables)}")
    print(f"Tabelas copiaveis no PostgreSQL: {len(tables_to_copy)}")

    if missing_in_pg:
        print("Tabelas ignoradas (nao existem no PostgreSQL):")
        for t in missing_in_pg:
            print(f"  - {t}")

    if not tables_to_copy:
        raise SystemExit("Nenhuma tabela em comum para copiar.")

    if not args.no_truncate:
        print("\nLimpando tabelas de destino (TRUNCATE ... CASCADE)...")
        truncate_target_tables(pg_engine, tables_to_copy)

    total = 0
    for table_name in tables_to_copy:
        common_cols = get_common_columns(sqlite_engine, pg_engine, table_name)
        if not common_cols:
            print(f"[SKIP] {table_name}: sem colunas em comum")
            continue

        rows = fetch_sqlite_rows(sqlite_engine, table_name, common_cols)
        count = insert_rows_in_batches(pg_engine, table_name, rows, args.batch_size)
        reset_sequence_if_needed(pg_engine, table_name)
        total += count
        print(f"[OK] {table_name}: {count} registros")

    print("\n" + "=" * 72)
    print(f"MIGRACAO CONCLUIDA: {total} registros inseridos")
    print("=" * 72)


if __name__ == "__main__":
    main()
