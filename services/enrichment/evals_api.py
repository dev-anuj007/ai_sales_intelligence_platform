from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/evals", tags=["evals"])


def get_evals_dir() -> Path:
    """Get path to evals directory."""
    return Path(__file__).parent / "evals"


@router.get("/datasets")
async def list_datasets() -> dict[str, Any]:
    """List available eval datasets."""
    datasets_dir = get_evals_dir() / "datasets"

    if not datasets_dir.exists():
        return {"datasets": [], "total": 0}

    datasets = []
    for file_path in datasets_dir.glob("*.jsonl"):
        if file_path.name != ".gitkeep":
            datasets.append({
                "name": file_path.stem,
                "path": str(file_path.relative_to(get_evals_dir().parent)),
                "size_bytes": file_path.stat().st_size,
            })

    return {
        "datasets": sorted(datasets, key=lambda x: x["name"]),
        "total": len(datasets),
    }


@router.get("/results")
async def list_results() -> dict[str, Any]:
    """List available eval results."""
    results_dir = get_evals_dir() / "results"

    if not results_dir.exists():
        return {"results": [], "total": 0}

    results = []
    for file_path in results_dir.glob("*.json"):
        if file_path.name != ".gitkeep":
            try:
                with open(file_path) as f:
                    data = json.load(f)
                results.append({
                    "name": file_path.stem,
                    "path": str(file_path.relative_to(get_evals_dir().parent)),
                    "data": data,
                })
            except json.JSONDecodeError:
                pass

    return {
        "results": sorted(results, key=lambda x: x["name"]),
        "total": len(results),
    }


@router.get("/results/{result_name}")
async def get_result(result_name: str) -> dict[str, Any]:
    """Get specific eval result."""
    results_dir = get_evals_dir() / "results"
    result_path = results_dir / f"{result_name}.json"

    if not result_path.exists():
        return {"error": f"Result {result_name} not found"}

    try:
        with open(result_path) as f:
            data = json.load(f)
        return {
            "name": result_name,
            "data": data,
        }
    except json.JSONDecodeError:
        return {"error": f"Failed to parse {result_name}"}
