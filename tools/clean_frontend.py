#!/usr/bin/env python3
"""Move diretórios e arquivos de frontend para archive/frontend.

Uso:
  python tools/clean_frontend.py --dry-run
  python tools/clean_frontend.py --dry-run --paths barbermove app/static
  python tools/clean_frontend.py    # executa a movimentação
"""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path('.').resolve()
ARCHIVE = ROOT / 'archive' / 'frontend'

DEFAULT_PATHS = [
    'barbermove',
    'app/static',
    'public',
    'build',
    'dist',
    'client',
    'frontend',
    'barbearia.html',
    'cliente.html',
    'barbeiro.html'
]


def git_branch_create(name):
    subprocess.check_call(['git','checkout','-b',name], cwd=ROOT)


def git_commit(msg):
    subprocess.check_call(['git','add','-A'], cwd=ROOT)
    try:
        subprocess.check_call(['git','commit','-m',msg], cwd=ROOT)
    except subprocess.CalledProcessError:
        print('No changes to commit or commit failed.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--paths', nargs='*')
    args = p.parse_args()

    paths = args.paths if args.paths else DEFAULT_PATHS
    existing = []
    for pat in paths:
        candidate = ROOT / pat
        if candidate.exists():
            existing.append(candidate)
        else:
            # try glob
            matched = list(ROOT.glob(pat))
            for m in matched:
                if m.exists():
                    existing.append(m)

    if not existing:
        print('Nenhum caminho frontend encontrado com os padrões informados.')
        return

    print('Encontrados os seguintes paths frontend:')
    for e in existing:
        print('-', e.relative_to(ROOT))

    if args.dry_run:
        print('\n[DRY-RUN] O seguinte seria movido para archive/frontend:')
        for e in existing:
            target = ARCHIVE / e.relative_to(ROOT)
            print(f'[DRY] {e.relative_to(ROOT)} -> {target.relative_to(ROOT)}')
        return

    # criar branch
    branch = 'cleanup/frontend-prune'
    print('Criando branch', branch)
    git_branch_create(branch)

    moved = []
    for e in existing:
        target = ARCHIVE / e.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(e), str(target))
            moved.append((e, target))
        except Exception as ex:
            print('Erro movendo', e, ex)

    git_commit('chore: move frontend files to archive/frontend')

    print('\nMovidos:')
    for s,t in moved:
        print(f'{s.relative_to(ROOT)} -> {t.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
