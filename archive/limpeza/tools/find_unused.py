#!/usr/bin/env python3
"""Detecta arquivos possivelmente não usados no repositório.

Heurística simples:
- percorre arquivos rastreados no diretório (ignora .git, .venv, archive)
- para cada arquivo de texto, procura ocorrências do seu nome (basename)
- se não houver referências, marca como candidato

Uso: python tools/find_unused.py > unused_candidates.txt
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {'.git', '.venv', 'venv', 'archive', '__pycache__', '.idea', '.vscode', 'node_modules'}
TEXT_EXT = {'.py', '.md', '.html', '.js', '.jsx', '.ts', '.tsx', '.css', '.json', '.yml', '.yaml', '.ini', '.cfg', '.txt', '.csv'}


def is_ignored(path: Path):
    for part in path.parts:
        if part in IGNORED_DIRS:
            return True
    return False


def list_files():
    for p in ROOT.rglob('*'):
        if p.is_file() and not is_ignored(p.relative_to(ROOT)):
            yield p


def is_text_file(path: Path):
    return path.suffix.lower() in TEXT_EXT


def file_content(path: Path):
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def main():
    files = list(list_files())
    names = {p: p.name for p in files}

    # Build a big corpus for fast search
    corpus = {}
    for p in files:
        if is_text_file(p):
            corpus[p] = file_content(p)

    candidates = []
    for p in files:
        name = p.name
        # skip obvious entrypoints and config
        if p.name in {'README.md', 'README', 'requirements.txt', 'pyproject.toml', 'setup.py'}:
            continue

        found = False
        # search in corpus except the file itself
        for doc, text in corpus.items():
            if doc == p:
                continue
            if name in text:
                found = True
                break

        if not found:
            candidates.append((p, p.suffix.lower()))

    # Print candidates grouped by extension
    by_ext = {}
    for p, ext in candidates:
        by_ext.setdefault(ext, []).append(str(p.relative_to(ROOT)))

    print('# Unused candidates (heurística)')
    for ext, items in sorted(by_ext.items(), key=lambda x: x[0]):
        print(f'\n## {ext} ({len(items)})')
        for it in items:
            print(it)


if __name__ == '__main__':
    main()
