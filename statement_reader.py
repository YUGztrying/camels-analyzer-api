"""
Statement Reader — extracts a flat financial dict from the Spreading App's
financial_statements table (JSONB line_items + periods arrays).

The Spreading App stores one row per (user_id, company_name, statement_type).
Each row has:
  - periods:    text[]    e.g. ["2022-12-31", "2023-12-31"]
  - line_items: jsonb[]   each with {poste, description, amounts[], brut_amount, amort_prov_amount, net_amount}

This module fetches all 4 statement types, finds the period index, extracts
values by poste code using poste_mapping, and returns a flat dict ready for
camels_calculator.py.
"""
import logging
from supabase_client import get_client
from poste_mapping import get_mapping, compute_derived_fields

logger = logging.getLogger(__name__)


def _extract_value(item: dict, period_idx: int, use: str = "amounts") -> float:
    """
    Extract a numeric value from a line_item at the given period index.

    use='amounts'          → item['amounts'][period_idx]  (default)
    use='brut_amount'      → item['brut_amount'][period_idx] if available
    use='amort_prov_amount' → item['amort_prov_amount'][period_idx] if available
    use='net_amount'       → item['net_amount'][period_idx] if available

    Falls back to 'amounts' if the requested field is None or missing.
    """
    # Try the requested field first
    if use != "amounts":
        arr = item.get(use)
        if arr and isinstance(arr, list) and period_idx < len(arr):
            val = arr[period_idx]
            if val is not None:
                return float(val)

    # Fallback to amounts
    amounts = item.get("amounts")
    if amounts and isinstance(amounts, list) and period_idx < len(amounts):
        val = amounts[period_idx]
        if val is not None:
            return float(val)

    return 0.0


def _build_poste_lookup(line_items: list, period_idx: int) -> dict:
    """
    Build a dict: {poste_code: value} from line_items at the given period.
    Also stores brut/amort/net variants as poste_code__brut, etc.
    """
    lookup = {}
    for item in line_items:
        poste = item.get("poste")
        if not poste:
            continue

        lookup[poste] = _extract_value(item, period_idx, "amounts")

        # Store brut/amort/net variants for bank assets
        for variant in ("brut_amount", "amort_prov_amount", "net_amount"):
            arr = item.get(variant)
            if arr and isinstance(arr, list) and period_idx < len(arr):
                val = arr[period_idx]
                if val is not None:
                    lookup[f"{poste}__{variant}"] = float(val)

    return lookup


def _resolve_mapping_entry(entry, lookup: dict) -> float:
    """
    Resolve a single mapping entry against the poste lookup.

    entry can be:
      - str: single poste code → lookup[code]
      - list: sum of poste codes → sum(lookup[code] for code in list)
      - dict: {"poste": code, "use": "brut_amount"} → lookup[code__brut_amount]
      - None: skip (computed later)
    """
    if entry is None:
        return None

    if isinstance(entry, str):
        if entry.startswith("_compute"):
            return None  # handled by compute_derived_fields
        return lookup.get(entry, 0.0)

    if isinstance(entry, list):
        return sum(lookup.get(code, 0.0) for code in entry)

    if isinstance(entry, dict):
        poste = entry["poste"]
        use = entry.get("use", "amounts")
        # Try the specific variant key first
        variant_key = f"{poste}__{use}"
        if variant_key in lookup:
            return lookup[variant_key]
        # Fallback to the regular amounts value
        return lookup.get(poste, 0.0)

    return 0.0


def extract_statement_data(
    user_id: str,
    company_name: str,
    period: str,
    type_institution: str = None,
) -> dict:
    """
    Fetch financial data from Supabase and return a flat dict for the calculator.

    Parameters
    ----------
    user_id : str           UUID of the user
    company_name : str      Company name (join key with Spreading App)
    period : str            ISO date string, e.g. "2023-12-31"
    type_institution : str  "banque" or "microfinance" (auto-detected if None)

    Returns
    -------
    dict with all fields camels_calculator.py expects, plus metadata.
    """
    sb = get_client()

    # Fetch all statement types for this company/user
    result = (
        sb.table("financial_statements")
        .select("statement_type, periods, line_items, type_institution")
        .eq("user_id", user_id)
        .eq("company_name", company_name)
        .execute()
    )

    if not result.data:
        raise ValueError(f"No financial statements found for {company_name}")

    # Auto-detect type_institution from the data if not provided
    if not type_institution:
        type_institution = result.data[0].get("type_institution", "banque")

    mapping = get_mapping(type_institution)

    # Build a unified poste lookup across all statement types
    unified_lookup = {}
    found_period = False

    for row in result.data:
        periods = row.get("periods", [])
        if period not in periods:
            continue
        found_period = True
        period_idx = periods.index(period)

        line_items = row.get("line_items", [])
        if not line_items:
            continue

        stmt_lookup = _build_poste_lookup(line_items, period_idx)
        unified_lookup.update(stmt_lookup)

    if not found_period:
        available = set()
        for row in result.data:
            available.update(row.get("periods", []))
        raise ValueError(
            f"Period {period} not found. Available: {sorted(available)}"
        )

    # Apply the mapping to produce the flat dict
    data = {}
    for field_name, entry in mapping.items():
        val = _resolve_mapping_entry(entry, unified_lookup)
        if val is not None:
            data[field_name] = val

    # Add metadata
    data["bank_name"] = company_name
    data["name"] = company_name
    data["fiscal_year"] = period[:4]  # e.g. "2023" from "2023-12-31"
    data["currency"] = "XOF"
    data["type_institution"] = type_institution

    # Compute derived fields
    data = compute_derived_fields(data, type_institution)

    return data


def extract_previous_period_data(
    user_id: str,
    company_name: str,
    current_period: str,
    type_institution: str,
) -> dict | None:
    """
    Try to extract data for the previous year.
    Returns None if no previous period data is available.
    """
    # Parse year and go back one year
    try:
        year = int(current_period[:4])
        prev_period = current_period.replace(str(year), str(year - 1))
    except (ValueError, IndexError):
        return None

    try:
        return extract_statement_data(user_id, company_name, prev_period, type_institution)
    except ValueError:
        logger.info(f"No previous period data for {prev_period}")
        return None


def extract_all_periods_data(
    user_id: str,
    company_name: str,
    type_institution: str = None,
) -> tuple[list[dict], list[str], str]:
    """
    Extract financial data for ALL available periods in one DB query.

    Returns (statements, periods, type_institution) where *statements* is a
    list of flat dicts (one per period, sorted chronologically).
    """
    sb = get_client()
    result = (
        sb.table("financial_statements")
        .select("statement_type, periods, line_items, type_institution")
        .eq("user_id", user_id)
        .eq("company_name", company_name)
        .execute()
    )
    if not result.data:
        raise ValueError(f"No financial statements found for {company_name}")

    if not type_institution:
        type_institution = result.data[0].get("type_institution", "banque")

    # Union of all periods across statement types
    all_periods: set[str] = set()
    for row in result.data:
        all_periods.update(row.get("periods", []))
    all_periods_sorted = sorted(all_periods)  # chronological

    mapping = get_mapping(type_institution)

    statements: list[dict] = []
    for period in all_periods_sorted:
        unified_lookup: dict = {}
        found = False
        for row in result.data:
            periods = row.get("periods", [])
            if period not in periods:
                continue
            found = True
            period_idx = periods.index(period)
            line_items = row.get("line_items", [])
            if not line_items:
                continue
            unified_lookup.update(_build_poste_lookup(line_items, period_idx))

        if not found:
            continue

        data: dict = {}
        for field_name, entry in mapping.items():
            val = _resolve_mapping_entry(entry, unified_lookup)
            if val is not None:
                data[field_name] = val

        data["bank_name"] = company_name
        data["name"] = company_name
        data["fiscal_year"] = period[:4]
        data["period"] = period
        data["currency"] = "XOF"
        data["type_institution"] = type_institution
        data = compute_derived_fields(data, type_institution)
        statements.append(data)

    return statements, all_periods_sorted, type_institution


def period_label(period_str: str) -> str:
    """Convert ISO date to short label: '2023-12-31' → 'FY23', '2024-06-30' → 'HY24'."""
    month = int(period_str[5:7])
    year = period_str[2:4]
    if month == 12:
        return f"FY{year}"
    if month == 6:
        return f"HY{year}"
    if month == 3:
        return f"Q1{year}"
    if month == 9:
        return f"Q3{year}"
    return period_str


def list_companies_for_user(user_id: str) -> list:
    """List companies available for a user, using the user_companies view."""
    sb = get_client()
    result = (
        sb.table("user_companies")
        .select("user_id, company_name, type_institution, statement_count, last_updated")
        .eq("user_id", user_id)
        .order("company_name")
        .execute()
    )
    return result.data or []


def list_periods_for_company(user_id: str, company_name: str) -> list:
    """List available periods for a company (union across all statement types)."""
    sb = get_client()
    result = (
        sb.table("financial_statements")
        .select("periods")
        .eq("user_id", user_id)
        .eq("company_name", company_name)
        .execute()
    )

    all_periods = set()
    for row in result.data or []:
        all_periods.update(row.get("periods", []))

    return sorted(all_periods, reverse=True)
