"""Writes a JSON file so that a reader never sees half of it."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from app.application.documents import JsonObject


def write_json_atomically(path: Path, data: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write beside the target and replace; NaN is refused because it is not JSON.
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, allow_nan=False)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
