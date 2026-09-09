from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Generator

import orjson
import zstandard

import logfire


def iter_records(
    path: Path | str, limit: int | None = None
) -> Generator[dict[str, Any], None, None]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    dctx = zstandard.ZstdDecompressor()
    count = 0

    try:
        with open(path, "rb") as fh:
            with dctx.stream_reader(fh) as zfh:
                text = io.TextIOWrapper(zfh, encoding="utf-8", errors="replace")

                for line_num, line in enumerate(text, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = orjson.loads(line)
                        yield record
                        count += 1

                        if limit is not None and count >= limit:
                            break

                    except orjson.JSONDecodeError as e:
                        logfire.warning(
                            "stream_reader.bad_json_line", line_num=line_num, error=str(e)
                        )
                        continue

        logfire.info("stream_reader.complete", records_yielded=count, path=str(path))

    except Exception as e:
        logfire.error("stream_reader.failed", error=str(e), path=str(path))
        raise


def iter_batches(
    path: Path | str, batch_size: int = 5000, limit: int | None = None
) -> Generator[list[dict[str, Any]], None, None]:
    batch: list[dict[str, Any]] = []

    for record in iter_records(path, limit=limit):
        batch.append(record)

        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch
