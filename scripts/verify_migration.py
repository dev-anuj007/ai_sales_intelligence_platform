#!/usr/bin/env python
"""Verify PostgreSQL migration setup."""

from __future__ import annotations

import sys

from config import settings


def check_imports() -> bool:
    """Check if all imports work."""
    print("\n🔍 Checking imports...")
    try:
        from services.storage import (
            AccountStorageService,
            StagingStorageService,
            TraceStorageService,
            NamesStorageServiceImpl,
        )
        print("  ✓ Storage services imported")

        from services.storage.factory import get_pool, init_pool
        print("  ✓ Factory functions imported")

        from services.storage.sqlmodel_models import (
            AccountSQL,
            StagingRecordSQL,
            TraceRecordSQL,
            AccountTopRecordSQL,
        )
        print("  ✓ SQLModel ORM models imported")

        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def check_config() -> bool:
    """Check database configuration."""
    print("\n🔍 Checking configuration...")
    print(f"  Database type: {settings.db_type}")

    if settings.db_type == "postgres":
        print(f"  PostgreSQL Host: {settings.postgres_host}:{settings.postgres_port}")
        print(f"  Database: {settings.postgres_database}")
        print(f"  User: {settings.postgres_user}")
        print("  ✓ PostgreSQL configured")
        return True
    elif settings.db_type == "duckdb":
        print(f"  DuckDB path: {settings.duckdb_path}")
        print("  ✓ DuckDB configured (fallback)")
        return True
    else:
        print(f"  ✗ Unknown database type: {settings.db_type}")
        return False


def check_duckdb_fallback() -> bool:
    """Check if DuckDB fallback works."""
    print("\n🔍 Checking DuckDB fallback...")
    try:
        from services.storage.duckdb_connection import DuckDBConnectionPool
        print("  ✓ DuckDB connection pool available")
        return True
    except ImportError as e:
        print(f"  ✗ DuckDB import failed: {e}")
        return False


def check_factory_selection() -> bool:
    """Check if factory selects correct backend."""
    print("\n🔍 Checking factory backend selection...")
    try:
        from services.storage.factory import AccountStorageService, get_pool

        backend_name = AccountStorageService.__module__.split(".")[-1]
        print(f"  Selected backend: {backend_name}")

        if settings.db_type == "postgres":
            if "postgres" in backend_name.lower():
                print("  ✓ PostgreSQL backend selected")
                return True
            else:
                print(f"  ✗ Expected PostgreSQL backend, got {backend_name}")
                return False
        else:
            if "duckdb" in backend_name.lower() or "account_storage" in backend_name:
                print("  ✓ DuckDB backend selected (fallback)")
                return True
            else:
                print(f"  ✗ Expected DuckDB backend, got {backend_name}")
                return False
    except Exception as e:
        print(f"  ✗ Factory check failed: {e}")
        return False


def main() -> None:
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("PostgreSQL Migration Verification")
    print("=" * 60)

    checks = [
        ("Import check", check_imports),
        ("Configuration check", check_config),
        ("DuckDB fallback", check_duckdb_fallback),
        ("Factory selection", check_factory_selection),
    ]

    results = []
    for name, check_fn in checks:
        results.append((name, check_fn()))

    print("\n" + "=" * 60)
    print("Results:")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("=" * 60 + "\n")

    if all_passed:
        print("✅ All verification checks passed!")
        print("\nNext steps:")
        print("  1. Configure .env with DB_TYPE (postgres or duckdb)")
        print("  2. If using PostgreSQL, run: uv run python scripts/setup_postgres.py")
        print("  3. Start API: uv run uvicorn main:app --reload --port 8001")
        sys.exit(0)
    else:
        print("❌ Some verification checks failed!")
        print("See output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
