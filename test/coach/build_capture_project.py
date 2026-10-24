"""Give the real URecord integration test the game's circular-unit build order.

Run after configure, then compile the generated DPR with the game's FPC flags.
No runtime or capture implementation is stubbed.
"""

import sys
from pathlib import Path


def generate(root: Path) -> Path:
    source = (root / "src/ultrastardx.dpr").read_text(encoding="utf-8")
    uses = source[source.index("\nuses\n") : source.index("\nconst\n")]
    body = (root / "test/coach/coach_capture_test.pas").read_text(encoding="utf-8")
    body = body[body.index("\nvar\n") :]
    # Math is used by the fixture; all application units keep their build order.
    uses = uses.replace("  SysUtils;", "  Math, SysUtils;")
    target = root / "src/coach_capture_runtime.dpr"
    target.write_text(
        "program coach_capture_runtime;\n{$mode delphi}\n{$I switches.inc}\n"
        + uses
        + body,
        encoding="utf-8",
    )
    return target


if __name__ == "__main__":
    print(generate(Path(sys.argv[1]).resolve()))
