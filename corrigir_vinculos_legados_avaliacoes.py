"""
Correcao de vinculos legados para fluxo de avaliacoes.

Objetivo:
- Garantir que todo usuario barbeiro referenciado em chamados tenha registro em freelancers.
- Reportar barbearias sem usuario_id para tratamento manual seguro.

Uso:
    c:/projeto_barbearia/.venv/Scripts/python.exe corrigir_vinculos_legados_avaliacoes.py --dry-run
    c:/projeto_barbearia/.venv/Scripts/python.exe corrigir_vinculos_legados_avaliacoes.py --apply
"""

import argparse

from app.database import SessionLocal
from app.models import Barbearia, Chamado, Freelancer, Usuario


def corrigir_vinculos(apply_changes: bool) -> None:
    db = SessionLocal()
    criados = 0
    barbeiros_sem_usuario = 0
    ids_que_seriam_criados = []

    try:
        # Barbeiros realmente usados nos chamados (histórico operacional).
        barbeiro_ids = [
            row[0]
            for row in db.query(Chamado.barbeiro_id)
            .filter(Chamado.barbeiro_id.isnot(None))
            .distinct()
            .all()
        ]

        for usuario_id in barbeiro_ids:
            usuario = (
                db.query(Usuario)
                .filter(Usuario.id == usuario_id, Usuario.tipo == "barbeiro")
                .first()
            )

            if not usuario:
                barbeiros_sem_usuario += 1
                continue

            existente = (
                db.query(Freelancer)
                .filter(Freelancer.usuario_id == usuario_id)
                .first()
            )

            if existente:
                continue

            ids_que_seriam_criados.append(usuario_id)
            if apply_changes:
                db.add(
                    Freelancer(
                        usuario_id=usuario_id,
                        tempo_experiencia_anos=1,
                        nivel_tecnico="intermediario",
                        comissao_ativa=False,
                        status_pausado=False,
                    )
                )
            criados += 1

        if apply_changes:
            db.commit()
        else:
            db.rollback()

        barbearias_sem_dono = (
            db.query(Barbearia)
            .filter(Barbearia.usuario_id.is_(None))
            .count()
        )

        modo = "APPLY" if apply_changes else "DRY-RUN"
        print("=== CORRECAO DE VINCULOS (AVALIACOES) ===")
        print(f"Modo: {modo}")
        print(f"Freelancers criados: {criados}")
        if ids_que_seriam_criados:
            print(f"IDs de usuario afetados: {ids_que_seriam_criados}")
        print(f"Barbeiros sem usuario valido: {barbeiros_sem_usuario}")
        print(f"Barbearias sem usuario_id (pendente manual): {barbearias_sem_dono}")
        print("Status: OK")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Corrige vinculos legados do fluxo de avaliacoes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Somente audita e mostra o que seria alterado (padrao)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica as alteracoes no banco",
    )
    args = parser.parse_args()

    aplicar = args.apply and not args.dry_run
    corrigir_vinculos(apply_changes=aplicar)
