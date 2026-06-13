"""Phase 0 smoke test — proves every credential and library is wired up.

Run after .env is filled in:
    python scripts/00_smoke_test.py

Exits 0 if all three components respond. Prints what failed otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/00_smoke_test.py` from the repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rich.console import Console  # noqa: E402

console = Console()


def check_aura() -> bool:
    try:
        from gymbuddy.graph_client import run

        res = run("MATCH (n) RETURN count(n) AS n LIMIT 1")
        n = res.records[0]["n"]
        console.print(f"[green]✅ Aura connected[/green] ({n} nodes currently)")
        return True
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]❌ Aura failed:[/red] {type(e).__name__}: {e}")
        return False


def check_groq() -> bool:
    try:
        from groq import Groq

        from gymbuddy.config import settings

        client = Groq(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": "Say 'hi' in exactly one word."}],
            max_tokens=8,
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        console.print(f"[green]✅ Groq responds[/green] ({settings.groq_model}) → {text!r}")
        return True
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]❌ Groq failed:[/red] {type(e).__name__}: {e}")
        return False


def check_embeddings() -> bool:
    try:
        from sentence_transformers import SentenceTransformer

        from gymbuddy.config import settings

        console.print("[dim]  Loading MiniLM (first run: ~90 MB download)…[/dim]")
        model = SentenceTransformer(settings.embedding_model)
        vec = model.encode("Barbell Bench Press", normalize_embeddings=True)
        console.print(
            f"[green]✅ Embeddings loaded[/green] ({settings.embedding_model}, "
            f"dim={len(vec)})"
        )
        return True
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]❌ Embeddings failed:[/red] {type(e).__name__}: {e}")
        return False


def main() -> int:
    console.rule("[bold]GymBuddy — Phase 0 smoke test[/bold]")

    results = {
        "Aura":       check_aura(),
        "Groq":       check_groq(),
        "Embeddings": check_embeddings(),
    }

    console.rule()
    n_ok = sum(results.values())
    if n_ok == len(results):
        console.print(f"[bold green]All {n_ok}/{len(results)} checks passed.[/bold green]")
        return 0
    failed = [name for name, ok in results.items() if not ok]
    console.print(
        f"[bold red]{len(failed)} of {len(results)} failed: {', '.join(failed)}[/bold red]"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
