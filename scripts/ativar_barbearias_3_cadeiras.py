"""
Ativa todas as barbearias ja cadastradas (perfil_aprovado = True) e garante
3 cadeiras disponiveis por barbearia, reutilizando cadeiras existentes.

Nao cria barbearias novas. Nao cria cadeiras alem do necessario pra chegar a 3.
Nao mexe em cadeiras OCUPADA (atendimento em andamento) nem em servicos,
precos, avaliacoes, localizacao, chamados, matching ou pagamentos.

Uso:
    DATABASE_URL=<postgres_url> python scripts/ativar_barbearias_3_cadeiras.py --dry-run
    DATABASE_URL=<postgres_url> python scripts/ativar_barbearias_3_cadeiras.py
"""
import sys
from datetime import datetime

from app.database import SessionLocal
from app import models

CADEIRAS_ALVO = 3


def ativar_barbearias(db, dry_run: bool) -> int:
    usuarios_barbearia = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbearia",
        models.Usuario.perfil_aprovado != True,  # noqa: E712
    ).all()

    for usuario in usuarios_barbearia:
        print(f"  ativar usuario_id={usuario.id} nome={usuario.nome!r}")
        if not dry_run:
            usuario.perfil_aprovado = True
            if not usuario.perfil_aprovado_em:
                usuario.perfil_aprovado_em = datetime.now()

    return len(usuarios_barbearia)


def garantir_3_cadeiras(db, dry_run: bool) -> tuple[int, int]:
    barbearias = db.query(models.Barbearia).all()
    total_reativadas = 0
    total_criadas = 0

    for barbearia in barbearias:
        cadeiras = db.query(models.Cadeira).filter(
            models.Cadeira.barbearia_id == barbearia.id
        ).order_by(models.Cadeira.numero.asc()).all()

        usaveis = [c for c in cadeiras if c.status in (
            models.StatusCadeira.DISPONIVEL.value,
            models.StatusCadeira.OCUPADA.value,
        )]
        bloqueadas = [c for c in cadeiras if c.status == models.StatusCadeira.BLOQUEADA.value]

        faltam = CADEIRAS_ALVO - len(usaveis)
        if faltam <= 0:
            continue

        print(f"  barbearia_id={barbearia.id} nome={barbearia.nome!r}: "
              f"{len(usaveis)} usavel(is), {len(bloqueadas)} bloqueada(s) -> faltam {faltam}")

        # 1) Reaproveita cadeiras bloqueadas existentes primeiro.
        for cadeira in bloqueadas:
            if faltam <= 0:
                break
            print(f"    reativar cadeira_id={cadeira.id} numero={cadeira.numero} (era bloqueada)")
            if not dry_run:
                cadeira.status = models.StatusCadeira.DISPONIVEL.value
            faltam -= 1
            total_reativadas += 1

        # 2) Cria só as cadeiras que ainda faltarem pra chegar a 3.
        if faltam > 0:
            proximo_numero = max((c.numero for c in cadeiras), default=0) + 1
            for _ in range(faltam):
                print(f"    criar cadeira numero={proximo_numero} para barbearia_id={barbearia.id}")
                if not dry_run:
                    db.add(models.Cadeira(
                        barbearia_id=barbearia.id,
                        numero=proximo_numero,
                        status=models.StatusCadeira.DISPONIVEL.value,
                    ))
                proximo_numero += 1
                total_criadas += 1

    return total_reativadas, total_criadas


def main():
    dry_run = "--dry-run" in sys.argv
    db = SessionLocal()
    try:
        print(f"=== Ativando barbearias {'(dry-run)' if dry_run else ''} ===")
        n_ativadas = ativar_barbearias(db, dry_run)

        print(f"=== Garantindo {CADEIRAS_ALVO} cadeiras por barbearia {'(dry-run)' if dry_run else ''} ===")
        n_reativadas, n_criadas = garantir_3_cadeiras(db, dry_run)

        if dry_run:
            db.rollback()
            print("\n(dry-run: nenhuma alteracao foi salva)")
        else:
            db.commit()
            print("\nAlteracoes salvas.")

        print(f"\nResumo: {n_ativadas} barbearia(s) ativada(s), "
              f"{n_reativadas} cadeira(s) reativada(s), {n_criadas} cadeira(s) criada(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
