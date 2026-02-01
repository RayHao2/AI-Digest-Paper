from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List
import typer
from dotenv import load_dotenv
from rich import print
from paper_digest.graph.build_graph import build
from dotenv import load_dotenv

load_dotenv()
app = typer.Typer(add_completion=False)
@app.command()
def run(
    top_k: int = typer.Option(5, help="How many papers to include in the digest."),
    max_results: int = typer.Option(20, help="How many papers to fetch from arXiv."),
    topic: List[str] = typer.Option([], help="Repeatable. Keywords to match in title/abstract."),
):

    """
    Run the paper digest pipeline once (MVP stub).
    """
    load_dotenv()

    graph = build()

    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_dir = str(Path("outputs") / f"run_{run_id}")
    initial_state = {
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "top_k": top_k,
        "max_results": max_results,
        "topics": topic,
        "errors": [],
        "logs": [],
        "llm_model": "gemini-2.5-flash",
        "run_id": run_id,
        "out_dir": out_dir
    }

    result = graph.invoke(initial_state)

    # Print digest to terminal
    digest = result.get("digest_md", "")
    print("[bold green]✅ Run complete[/bold green]\n")
    print(digest)

    # Helpful note about output directory
    out_dir = Path("outputs").resolve()
    print(f"\n[dim]Saved digest to: {out_dir}[/dim]")

    # Optional: show logs if any
    logs = result.get("logs", [])
    if logs:
        print("\n[bold]Logs:[/bold]")
        for line in logs:
            print(f"- {line}")


def main():
    app()

if __name__ == "__main__":
    main()

