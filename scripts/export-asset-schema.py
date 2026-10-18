#!/usr/bin/env python3
"""Write library/asset.schema.json, the JSON Schema of asset.json, from the pydantic model (design §5).

Run after changing src/hone_motif/asset.py: `uv run scripts/export-asset-schema.py`. The default suite
fails while the file is out of date.
"""

import json
from pathlib import Path

from hone_motif.asset import Asset

out = Path(__file__).parent.parent / "library" / "asset.schema.json"
out.write_text(
    json.dumps(Asset.model_json_schema(by_alias=True), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(f"wrote {out}")
