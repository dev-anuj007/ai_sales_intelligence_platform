"""CLI entry point for the data pipeline.

Usage:
    uv run python -m sales_intel.services.pipeline.run_pipeline --input data/fixtures/shodan_sample.jsonl --db db/sales_intel.duckdb --limit 5000
    uv run python -m sales_intel.services.pipeline.run_pipeline --input $RAW_DATA_PATH --db db/sales_intel.duckdb
"""

from pathlib import Path

import typer

import logfire

from sales_intel.config import settings
from sales_intel.data.connection import get_connection_context
from sales_intel.data.migrate import apply_schema
from sales_intel.data.staging_repo import StagingRecordRepository
from sales_intel.services.aggregation.aggregation_service import AggregationService
from sales_intel.services.pipeline.ingest_service import IngestService

app = typer.Typer(help="Data pipeline: ingest, normalize, aggregate")


@app.command()
def pipeline(
    input: str = typer.Option(
        ...,
        "--input",
        help="Path to zstd-compressed JSONL file (e.g., data/fixtures/shodan_sample.jsonl)",
    ),
    db: str = typer.Option(
        str(settings.duckdb_path),
        "--db",
        help="Path to DuckDB file",
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
    db_path = Path(db)

    if not input_path.exists():
        typer.echo(f"❌ Input file not found: {input_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"🚀 Starting pipeline")
    typer.echo(f"   Input: {input_path}")
    typer.echo(f"   DB: {db_path}")
    if limit:
        typer.echo(f"   Limit: {limit} records")

    try:
        with get_connection_context() as conn:
            # Ensure schema exists
            typer.echo("📋 Applying schema...")
            apply_schema(conn)

            # Phase 1: Ingest
            typer.echo("📥 Ingesting records...")
            staging_repo = StagingRecordRepository(conn)
            ingest_service = IngestService(staging_repo)
            ingest_result = ingest_service.ingest(
                input_path, batch_size=batch_size, limit=limit
            )

            typer.echo(f"✅ Ingest complete: {ingest_result['total_inserted']} records inserted")

            # Phase 2: Aggregate
            typer.echo("🔄 Aggregating into accounts...")
            agg_service = AggregationService(conn)
            agg_result = agg_service.aggregate_staging_to_accounts()

            typer.echo(f"✅ Aggregation complete:")
            typer.echo(f"   - {agg_result['accounts_created']} accounts created")
            typer.echo(f"   - {agg_result['excluded_as_honeypot']} excluded as honeypots")

            # Summary
            typer.echo("\n✨ Pipeline complete!")
            typer.echo(f"\nNext steps:")
            typer.echo(f"  1. Score accounts: python -m sales_intel.services.scoring.score_accounts --db {db}")
            typer.echo(f"  2. Enrich top accounts: python -m sales_intel.services.enrichment.run_enrichment --db {db} --top-n 50")
            typer.echo(f"  3. Start API: uvicorn main:app --reload")

    except Exception as e:
        typer.echo(f"❌ Pipeline failed: {e}", err=True)
        logfire.error("pipeline.failed", error=str(e))
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
