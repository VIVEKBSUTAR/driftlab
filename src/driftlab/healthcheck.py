"""Authenticated readiness probe for a local server process."""

import urllib.request
from driftlab.config.settings import Settings


def main():
    settings = Settings.from_env()
    key = settings.api_key.get_secret_value() if settings.api_key else ""
    request = urllib.request.Request(
        "http://127.0.0.1:8000/api/readyz",
        headers={"Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(request, timeout=4) as response:
        if response.status != 200:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
