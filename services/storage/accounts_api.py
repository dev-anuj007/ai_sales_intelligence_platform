from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from services.storage import AccountStorageService

router = APIRouter(prefix="/accounts", tags=["accounts"])


def get_account_storage() -> AccountStorageService:
    return AccountStorageService()


@router.get("")
async def list_accounts(
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    sort: str = Query("root_domain", pattern="^(root_domain|risk_score_desc|risk_score_asc)$"),
    storage: AccountStorageService = Depends(get_account_storage),
) -> dict[str, Any]:
    """List accounts with optional sorting and pagination."""
    if sort == "risk_score_desc":
        accounts = storage.list_top_by_score(top_n=limit)
    elif sort == "risk_score_asc":
        accounts = storage.list_by_score(limit=limit)
    else:
        accounts = storage.list(limit=limit, offset=offset)

    return {
        "total": storage.count(),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "root_domain": a.root_domain,
                "risk_score": a.risk_score,
                "signal_tags": a.signal_tags,
                "asset_count": a.asset_count,
                "vuln_count_total": a.vuln_count_total,
                "inferred_company_name": a.inferred_company_name,
                "inferred_industry": a.inferred_industry,
            }
            for a in accounts
        ],
    }


@router.get("/{root_domain}")
async def get_account(
    root_domain: str,
    storage: AccountStorageService = Depends(get_account_storage),
) -> dict[str, Any]:
    """Get full account details including enrichment."""
    account = storage.get(root_domain)

    if not account:
        return {"error": f"Account {root_domain} not found"}

    return {
        "root_domain": account.root_domain,
        "record_count": account.record_count,
        "asset_count": account.asset_count,
        "distinct_ips": account.distinct_ips,
        "distinct_ports": account.distinct_ports,
        "port_list": account.port_list,
        "countries": account.countries,
        "primary_country_code": account.primary_country_code,
        "primary_org": account.primary_org,
        "cloud_or_cdn_fronted": account.cloud_or_cdn_fronted,
        "vuln_count_total": account.vuln_count_total,
        "vuln_count_critical": account.vuln_count_critical,
        "max_cvss": account.max_cvss,
        "max_epss": account.max_epss,
        "exposed_database_count": account.exposed_database_count,
        "legacy_protocol_count": account.legacy_protocol_count,
        "iot_ot_device_count": account.iot_ot_device_count,
        "risk_score": account.risk_score,
        "signal_tags": account.signal_tags,
        "score_explanation": account.score_explanation,
        "inferred_company_name": account.inferred_company_name,
        "inferred_industry": account.inferred_industry,
        "narrative": account.narrative,
        "outreach_draft": account.outreach_draft,
    }
