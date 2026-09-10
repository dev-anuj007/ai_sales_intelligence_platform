from __future__ import annotations

from pathlib import Path
from typing import Any

import logfire

from services.storage import StagingStorageService
from services.pipeline.normalizer import normalize_record
from services.pipeline.stream_reader import iter_batches


class IngestService:
    def __init__(self, staging_storage: StagingStorageService) -> None:
        self.staging_storage = staging_storage
        self.total_records_processed = 0
        self.total_records_inserted = 0

    def ingest(
        self,
        input_path: Path | str,
        batch_size: int = 5000,
        limit: int | None = None,
    ) -> dict[str, Any]:
        input_path = Path(input_path)
        logfire.info("ingest_service.start", path=str(input_path), limit=limit)

        record_id_counter = 1

        try:
            for batch in iter_batches(input_path, batch_size=batch_size, limit=limit):
                normalized_batch = []

                for raw_record in batch:
                    try:
                        normalized = normalize_record(raw_record, record_id_counter)
                        normalized_batch.append(normalized)
                        record_id_counter += 1
                        self.total_records_processed += 1

                    except Exception as e:
                        logfire.warning(
                            "ingest_service.normalize_failed",
                            error=str(e),
                            record_id=record_id_counter,
                        )
                        record_id_counter += 1
                        continue

                try:
                    inserted = self.staging_storage.bulk_insert(normalized_batch)
                    self.total_records_inserted += inserted
                    logfire.info("ingest_service.batch_inserted", count=inserted)

                except Exception as e:
                    logfire.error("ingest_service.bulk_insert_failed", error=str(e))
                    raise

            summary = {
                "status": "success",
                "total_processed": self.total_records_processed,
                "total_inserted": self.total_records_inserted,
                "failed": self.total_records_processed - self.total_records_inserted,
            }

            logfire.info("ingest_service.complete", **summary)
            return summary

        except Exception as e:
            logfire.error("ingest_service.failed", error=str(e))
            raise
