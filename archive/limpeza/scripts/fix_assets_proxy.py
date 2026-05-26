import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIRS = [ROOT / 'app' / 'static' / 'assets', ROOT / 'barbermove', ROOT / 'admin-panel']
JS_EXT = '.js'

# Patterns to replace: HTTP IP:8000 or localhost/127.0.0.1 -> /proxy
RE_PLAT = [
    (re.compile(r"https?://127\\.0\\.0\\.1:8000"), '/proxy'),
    (re.compile(r"https?://localhost:8000"), '/proxy'),
    (re.compile(r"https?://\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}:8000"), '/proxy'),
    # WS patterns -> /proxy/ws/notificacoes
    (re.compile(r"wss?://127\\.0\\.0\\.1:8000/ws/notificacoes"), '/proxy/ws/notificacoes'),
    (re.compile(r"wss?://localhost:8000/ws/notificacoes"), '/proxy/ws/notificacoes'),
    (re.compile(r"wss?://\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}:8000/ws/notificacoes"), '/proxy/ws/notificacoes'),
]


def process_file(p: Path):
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        return False, 'read_error'
    orig = text
    changed = text
    for pattern, repl in RE_PLAT:
        changed = pattern.sub(repl, changed)
    if changed != orig:
        bak = p.with_suffix(p.suffix + '.bak')
        bak.write_text(orig, encoding='utf-8')
        p.write_text(changed, encoding='utf-8')
        return True, 'modified'
    return False, 'nochange'


def main():
    modified = []
    for td in TARGET_DIRS:
        if not td.exists():
            continue
        for p in td.rglob(f'*{JS_EXT}'):
            ok, status = process_file(p)
            if ok and status == 'modified':
                modified.append(str(p.relative_to(ROOT)))
    print('Modified files:')
    for m in modified:
        print(m)

if __name__ == '__main__':
    main()
