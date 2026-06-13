"""Phase 3 — embed exercises with all-MiniLM-L6-v2 (384d).

    python scripts/03_embed.py

Reads  data/raw/exercises.json
Writes data/processed/exercise_embeddings.parquet  (exercise_id, embedding[384])

Runs in seconds for 873 rows. Embedding text = "<name>. <instructions>".
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
RAW = DATA_DIR / "raw" / "exercises.json"
OUT = DATA_DIR / "processed" / "exercise_embeddings.parquet"

MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def main() -> int:
    import pandas as pd
    from sentence_transformers import SentenceTransformer

    data = json.loads(RAW.read_text(encoding="utf-8"))
    ids = [e["id"] for e in data]
    texts = [
        f"{e.get('name', '')}. {' '.join(e.get('instructions') or [])}".strip()
        for e in data
    ]

    print(f"Loading {MODEL_NAME} …")
    model = SentenceTransformer(MODEL_NAME)
    print(f"Encoding {len(texts)} exercises …")
    vecs = model.encode(
        texts, normalize_embeddings=True, batch_size=64, show_progress_bar=True
    )
    dim = len(vecs[0])
    print(f"✅ encoded, dim={dim}")
    assert dim == 384, f"expected 384d, got {dim}"

    df = pd.DataFrame({"exercise_id": ids, "embedding": [v.tolist() for v in vecs]})
    df.to_parquet(OUT, index=False)
    print(f"✅ wrote {OUT} ({len(df)} rows)")

    # Sanity: nearest neighbours of a bench press should be other chest presses.
    import numpy as np

    mat = np.array(df["embedding"].tolist())
    try:
        anchor = ids.index("Barbell_Bench_Press_-_Medium_Grip")
        sims = mat @ mat[anchor]
        top = sims.argsort()[::-1][1:6]
        print("Nearest to Barbell Bench Press (Medium Grip):")
        names = {e["id"]: e["name"] for e in data}
        for i in top:
            print(f"   {names[ids[i]]}  ({sims[i]:.3f})")
    except ValueError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
