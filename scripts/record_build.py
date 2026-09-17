import json
import os
import sys

import httpx


def main() -> None:
    service_url = os.environ.get("DEVTOOL_SERVICE_URL", "http://127.0.0.1:8000")
    payload = {
        "event_id": "docs-site-2026-09-06-a1b2c3d",
        "project": "docs-site",
        "revision": "a1b2c3d4e5f6",
        "environment": "preview",
        "status": "succeeded",
        "summary": "Adds searchable API reference pages",
    }
    response = httpx.request(
        "POST",
        f"{service_url}/build-events",
        json=payload,
        timeout=60.0,
    )
    response.raise_for_status()
    json.dump(response.json(), sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()

