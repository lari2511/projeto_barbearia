#!/usr/bin/env python3
"""Heurística mais ampla para identificar arquivos não usados.

O que faz:
- coleta arquivos não rastreados pelo Git
- coleta arquivos não modificados nos últimos N dias (default 365)
- usa busca por nome (heurística anterior) para arquivos não referenciados
- une candidatos e move para `archive/limpeza/` mantendo estrutura
- cria branch `cleanup/auto-prune` e commita as mudanças

Uso: python tools/auto_clean.py --days 365 --dry-run
"""
import subprocess
import os
import sys
from pathlib import Path
import shutil
import argparse
import datetime

ROOT = Path('.').resolve()
ARCHIVE = ROOT / 'archive' / 'limpeza'
IGNORED_DIRS = {'.git', '.venv', 'venv', 'archive', '__pycache__', '.idea', '.vscode', 'node_modules'}
TEXT_EXT = {'.py', '.md', '.html', '.js', '.jsx', '.ts', '.tsx', '.css', '.json', '.yml', '.yaml', '.ini', '.cfg', '.txt', '.csv'}


def run(cmd):
    return subprocess.check_output(cmd, shell=True, cwd=ROOT, text=True)


def git_branch_create(name):
    run(f'git checkout -b {name}')


def git_commit_all(msg):
    run('git add -A')
    try:
        run(f'git commit -m "{msg}"')
    except subprocess.CalledProcessError:
        print('No changes to commit or commit failed.')


def is_ignored(path: Path):
    for part in path.parts:
        if part in IGNORED_DIRS:
            return True
    return False


def list_all_files():
    for p in ROOT.rglob('*'):
        if p.is_file() and not is_ignored(p.relative_to(ROOT)):
            yield p


def get_untracked():
    out = run('git ls-files --others --exclude-standard')
    return {ROOT / p.strip() for p in out.splitlines() if p.strip()}


def get_old_files(days):
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    res = set()
    for p in list_all_files():
        try:
            m = datetime.datetime.fromtimestamp(p.stat().st_mtime)
            if m < cutoff:
                res.add(p)
        except Exception:
            continue
    return res


def name_not_referenced():
    # reuse previous simple corpus search
    files = list(list_all_files())
    corpus = {}
    for p in files:
        if p.suffix.lower() in TEXT_EXT:
            try:
                corpus[p] = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                corpus[p] = ''

    candidates = set()
    for p in files:
        name = p.name
        if name in {'README.md', 'README', 'requirements.txt', 'pyproject.toml', 'setup.py'}:
            continue
        found = False
        for doc, text in corpus.items():
            if doc == p:
                continue
            if name in text:
                found = True
                break
        if not found:
            candidates.add(p)
    return candidates


def move_to_archive(paths, dry_run=True):
    moved = []
    for p in sorted(paths):
        rel = p.relative_to(ROOT)
        target = ARCHIVE / rel
        if dry_run:
            print(f'[DRY] Move {rel} -> {target.relative_to(ROOT)}')
            moved.append((p, target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(p), str(target))
            moved.append((p, target))
        except Exception as e:
            print('Failed to move', p, e)
    return moved


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--days', type=int, default=365)
    p.add_argument('--dry-run', action='store_true')
    return p.parse_args()


def main():
    args = parse_args()
    print('Collecting candidates...')
    untracked = get_untracked()
    print(f'untracked: {len(untracked)}')
    old = get_old_files(args.days)
    print(f'old (> {args.days} days): {len(old)}')
    name_unused = name_not_referenced()
    print(f'name-not-referenced: {len(name_unused)}')

    # combine
    candidates = set(untracked) | (old & name_unused) | untracked
    # filter out some important files
    ignore_names = {'manage.py', 'app.py', 'main.py'}
    candidates = {p for p in candidates if p.name not in ignore_names}

    print('\nTOTAL CANDIDATES:', len(candidates))

    if not candidates:
        print('No candidates found.')
        return

    if not args.dry_run:
        print('Creating branch cleanup/auto-prune')
        git_branch_create('cleanup/auto-prune')

    moved = move_to_archive(candidates, dry_run=args.dry_run)

    if not args.dry_run:
        git_commit_all('chore: move unused files to archive/limpeza')

    print('\nDone. Moved items:')
    for src, dst in moved:
        print(f'{src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
