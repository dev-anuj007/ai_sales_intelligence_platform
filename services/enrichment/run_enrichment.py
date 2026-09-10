from __future__ import annotations

import asyncio

import typer

import logfire

from config import settings
from services.storage import init_pool, close_pool
from services.enrichment.service import EnrichmentService

app = typer.Typer(help="Enrichment service: LLM-powered account analysis")


@app.command()
def enrich_accounts(
    top_n: int = typer.Option(
        50,
        "--top-n",
        help="Number of top-ranked accounts to enrich (by risk_score)",
    ),
) -> None:
    """Enrich top-N highest-risk accounts with LLM analysis.

    Enrichment includes:
    - Signal/noise re-classification (Haiku): validate that exposures are real
    - Company inference (Haiku): guess company name from domain + HTTP titles
    - Risk narrative (Sonnet): grounded explanation of the risk
    - Outreach draft (Sonnet): personalized cold-email template

    Mock client by default. Swap to real Anthropic API via LLM_CLIENT=anthropic
    once an ANTHROPIC_API_KEY is available.
    """
    typer.echo(f"Starting enrichment")
    typer.echo(f"   Database: PostgreSQL ({settings.postgres_database})")
    typer.echo(f"   Top N: {top_n}")

    try:
        pool = init_pool()

        typer.echo("Enriching top accounts...")
        enrichment_service = EnrichmentService()
        result = asyncio.run(enrichment_service.enrich_top_accounts(top_n=top_n))

        typer.echo(f"Enrichment complete:")
        typer.echo(f"   - {result['enriched_count']} accounts enriched")
        if "errors" in result and result["errors"]:
            typer.echo(f"   - {len(result['errors'])} errors")

        typer.echo("\nNext steps:")
        typer.echo(f"  1. Start API: uvicorn main:app --reload")
        typer.echo(f"  2. Query enriched accounts: curl http://localhost:8001/accounts?limit=10")

    except Exception as e:
        typer.echo(f"❌ Enrichment failed: {e}", err=True)
        logfire.error("enrichment.failed", error=str(e))
        raise typer.Exit(1)
    finally:
        close_pool()


if __name__ == "__main__":
    app()
