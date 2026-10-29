"""The plain-data type of a result document and of its parts."""

from __future__ import annotations

from typing import Any

# A JSON object: the result of a run is plain data that the adapters write and send as it is.
type JsonObject = dict[str, Any]
