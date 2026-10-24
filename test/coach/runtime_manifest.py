"""Bind a small native update to the exact CI-built game's files and DLLs."""

import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
game = root / "game"
files = {}
for path in sorted(game.rglob("*")):
    if not path.is_file():
        continue
    relative = path.relative_to(game)
    if relative.parts[0] in {"songs", "playlists", "screenshots"}:
        continue
    if path.name == "config.ini" or path.suffix.lower() in {".db", ".log"}:
        continue
    files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {
    "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip(),
    "files": files,
}
(root / "runtime-manifest.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)
