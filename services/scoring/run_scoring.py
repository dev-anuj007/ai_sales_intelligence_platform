from __future__ import annotations

import typer

import logfire

from config import settings
from services.storage import init_pool, close_pool
from services.scoring.service import ScoringService

app = typer.Typer(help="Scoring service: compute risk scores for accounts")


@app.command()
def score_accounts(
    score_version: str = typer.Option(
        "v1",
        "--version",
        help="Scoring version (for A/B testing different rule weights)",
    ),
) -> None:
    """Compute risk scores (0–100) for all unscored accounts.

    Scoring is rule-based and deterministic:
    - 35% vulnerability severity (CVSS × EPSS)
    - 25% exposable attack surface (DB, legacy protocols, IoT/OT)
    - 15% TLS/SSL hygiene (self-signed, weak versions)
    - 15% EOL/legacy product prevalence
    - 10% raw asset count (attack surface size)

    Scores are stored with signal_tags (audit trail) and score_explanation (breakdown).
    """
    typer.echo(f"Starting scoring")
    typer.echo(f"   Database: {settings.db_type}")
    typer.echo(f"   Score version: {score_version}")

    try:
        pool = init_pool()

        typer.echo("Scoring accounts...")
        scoring_service = ScoringService()
        result = scoring_service.score_accounts(score_version=score_version)

        typer.echo(f"Scoring complete:")
        typer.echo(f"   - {result['scores_applied']} accounts scored")
        typer.echo(f"   - Version: {result['score_version']}")

        typer.echo("\nNext steps:")
        typer.echo(f"  1. Enrich top accounts: python -m services.enrichment.run_enrichment --top-n 50")
        typer.echo(f"  2. Start API: uvicorn main:app --reload")

    except Exception as e:
        typer.echo(f"❌ Scoring failed: {e}", err=True)
        logfire.error("scoring.failed", error=str(e))
        raise typer.Exit(1)
    finally:
        close_pool()


if __name__ == "__main__":
    app()
