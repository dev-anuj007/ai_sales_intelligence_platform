from __future__ import annotations

from typing import Any, Generic, Protocol, TypeVar

from services.storage.enums import StorageType, TableType

T = TypeVar("T")


class StorageService(Protocol[T]):
    storage_type: StorageType
    table_type: TableType

    def get(self, id_value: Any) -> T | None: ...

    def list(self, limit: int = 100, offset: int = 0) -> list[T]: ...

    def create(self, entity: T) -> T: ...

    def update(self, entity: T) -> T: ...

    def delete(self, id_value: Any) -> bool: ...

    def count(self) -> int: ...


class NamesStorageService(Protocol):
    def store_name(self, root_domain: str, company_name: str, source: str) -> None: ...

    def get_name(self, root_domain: str) -> str | None: ...

    def list_by_pattern(self, pattern: str, limit: int = 100) -> dict[str, str]: ...

    def clear_cache(self) -> None: ...


class ConnectionPool(Protocol):
    def get_connection(self) -> Any: ...

    def close(self) -> None: ...
