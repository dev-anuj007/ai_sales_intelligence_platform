from __future__ import annotations

from pathlib import Path

import typer

import logfire

from config import settings
from services.storage import (
    StagingStorageService,
    init_pool,
    close_pool,
)
from services.storage.migrate import apply_schema
from services.aggregation.service import AggregationService
from services.pipeline.service import IngestService

app = typer.Typer(help="Data pipeline: ingest, normalize, aggregate")


@app.command()
def pipeline(
    input: str = typer.Option(
        ...,
        "--input",
        help="Path to zstd-compressed JSONL file (e.g., data/fixtures/shodan_sample.jsonl)",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        help="Max records to ingest (useful for dev iteration)",
    ),
    batch_size: int = typer.Option(
        settings.batch_size,
        "--batch-size",
        help="Records per batch for bulk insert",
    ),
) -> None:
    """Ingest data: stream records → normalize → insert staging → aggregate accounts.

    This is the main data pipeline. Runs in three phases:
    1. Stream Shodan records from zstd file
    2. Normalize each record (extract domain, features, etc.)
    3. Bulk insert into staging_records
    4. Aggregate staging into accounts table
    5. Build top-records index for LLM grounding
    """
    input_path = Path(input)

    if not input_path.exists():
        typer.echo(f"Input file not found: {input_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Starting pipeline")
    typer.echo(f"   Input: {input_path}")
    typer.echo(f"   Database: PostgreSQL ({settings.postgres_database})")
    if limit:
        typer.echo(f"   Limit: {limit} records")

    try:
        pool = init_pool()
        conn = pool.get_connection()

        typer.echo("Applying schema...")
        apply_schema()

        typer.echo("Ingesting records...")
        staging_storage = StagingStorageService(conn)
        ingest_service = IngestService(staging_storage)
        ingest_result = ingest_service.ingest(
            input_path, batch_size=batch_size, limit=limit
        )

        typer.echo(f"Ingest complete: {ingest_result['total_inserted']} records inserted")

        typer.echo("Aggregating into accounts...")
        agg_service = AggregationService()
        agg_result = agg_service.aggregate_staging_to_accounts()

        typer.echo(f"Aggregation complete:")
        typer.echo(f"   - {agg_result['accounts_created']} accounts created")
        typer.echo(f"   - {agg_result['excluded_as_honeypot']} excluded as honeypots")

        typer.echo("\nPipeline complete!")
        typer.echo(f"\nNext steps:")
        typer.echo(f"  1. Score accounts: python -m services.scoring.run_scoring")
        typer.echo(f"  2. Enrich top accounts: python -m services.enrichment.run_enrichment --top-n 50")
        typer.echo(f"  3. Start API: uvicorn main:app --reload")

    except Exception as e:
        typer.echo(f"❌ Pipeline failed: {e}", err=True)
        logfire.error("pipeline.failed", error=str(e))
        raise typer.Exit(1)
    finally:
        close_pool()


if __name__ == "__main__":
    app()
