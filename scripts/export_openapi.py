"""Export the public HTTP contract without opening or changing a workspace."""

import json
from pathlib import Path
from driftlab.api.main import create_app
from driftlab.config.settings import Settings

path = Path("docs/openapi.json")
path.write_text(
    json.dumps(create_app(Settings(worker_enabled=False)).openapi(), indent=2) + "\n",
    encoding="utf-8",
)
print(path)
