from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLOCKED_NAMES = re.compile(
    r"(^|/)(\.env($|\.)|[^/]*\.(db|sqlite|sqlite3|pem|p12|pfx|key|log)$|id_rsa($|\.))",
    re.IGNORECASE,
)
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
ASSIGNED_SECRET = re.compile(
    r"(?im)^\s*(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*=\s*['\"]?[^\s'\"]{12,}"
)
SOURCE_SECRET = re.compile(
    r'(?i)\b[\w]*(?:password|passphrase|secret|token|api_key)[\w]*\s*(?:\[\])?\s*=\s*"[^"\r\n]{8,}"'
)


def source_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return [item.decode("utf-8", errors="replace") for item in result.stdout.split(b"\0") if item]


def main() -> None:
    violations: list[str] = []
    files = source_files()
    for relative in files:
        normalized = relative.replace("\\", "/")
        if normalized != ".env.example" and BLOCKED_NAMES.search(normalized):
            violations.append(f"blocked tracked path: {relative}")
            continue
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PRIVATE_KEY.search(content):
            violations.append(f"private key material: {relative}")
        if relative != ".env.example" and ASSIGNED_SECRET.search(content):
            violations.append(f"probable assigned secret: {relative}")
        if path.suffix.lower() in {".c", ".cc", ".cpp", ".h", ".hpp", ".ino"} and SOURCE_SECRET.search(content):
            violations.append(f"probable compiled-in secret: {relative}")
    if violations:
        raise SystemExit("Source privacy gate failed:\n- " + "\n- ".join(violations))
    print(
        f"PRIVACY_OK: {len(files)} tracked and non-ignored source paths contain no "
        "blocked runtime data or obvious secrets."
    )


if __name__ == "__main__":
    main()
