from __future__ import annotations

import importlib
import sys
from pathlib import Path


CHECKS = [
    "schemas",
    "bus",
    "services.cvs",
    "services.policy",
    "services.cge",
    "services.dto",
    "services.vce",
    "services.do",
    "services.rrc",
    "services.api",
]


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    failures: list[tuple[str, str]] = []
    for module_name in CHECKS:
        try:
            importlib.import_module(module_name)
            print(f"[ok] {module_name}")
        except Exception as exc:
            failures.append((module_name, str(exc)))
            print(f"[fail] {module_name}: {exc}")

    if failures:
        print("\nValidation failed for these modules:")
        for module_name, error in failures:
            print(f"- {module_name}: {error}")
        return 1

    print("\nLocal import validation succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
