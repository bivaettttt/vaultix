import json
import sys
from pathlib import Path

from vaultix.api.main import app

target = Path("docs/api/openapi.json")
contents = (
    json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
)
if "--check" in sys.argv:
    if target.read_text() != contents:
        raise SystemExit(
            "OpenAPI drift. Regenerate with PYTHONPATH=backend python scripts/openapi.py"
        )
else:
    target.write_text(contents)
