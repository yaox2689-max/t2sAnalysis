"""Column name cleaner — sanitize Excel/CSV column names for SQL.

Handles: Chinese names, empty names, duplicates, special characters,
numeric prefixes.

Usage:
    from app.tools.column_cleaner import clean_column_names

    cleaned = clean_column_names(["销售额", "Sales Amount", "", "2024年"])
    # ["销售额", "sales_amount", "col_3", "year_2024"]
"""

import re
from typing import Optional


def clean_column_name(name: str, index: int, seen: set[str]) -> str:
    """Clean a single column name into a valid SQL identifier.

    Args:
        name: Original column name.
        index: Column position (0-based), used for fallback naming.
        seen: Set of already-used names (for deduplication).

    Returns:
        A cleaned, unique column name.
    """
    if not name or not str(name).strip():
        name = f"col_{index + 1}"
    else:
        name = str(name).strip()

    # Remove special characters, keep Chinese + letters + digits + underscore
    cleaned = re.sub(r"[^\w一-鿿]", "_", name)

    # Prefix if starts with digit (PRD: 2024年 → year_2024, generic: 123abc → n_123abc)
    if cleaned and cleaned[0].isdigit():
        if "年" in name:
            cleaned = f"year_{cleaned}"
        else:
            cleaned = f"n_{cleaned}"

    # Collapse consecutive underscores
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")

    # Fallback if empty after cleaning
    if not cleaned:
        cleaned = f"col_{index + 1}"

    # Lowercase for English names
    if cleaned.isascii():
        cleaned = cleaned.lower()

    # Deduplicate
    original = cleaned
    counter = 2
    while cleaned in seen:
        cleaned = f"{original}_{counter}"
        counter += 1

    seen.add(cleaned)
    return cleaned


def clean_column_names(names: list[str]) -> list[str]:
    """Clean a list of column names.

    Args:
        names: Original column names from Excel/CSV header.

    Returns:
        Cleaned, unique column names suitable for SQL.
    """
    seen: set[str] = set()
    return [clean_column_name(name, i, seen) for i, name in enumerate(names)]


def generate_table_name(file_name: str, sheet_name: Optional[str] = None) -> str:
    """Generate a readable DuckDB table name from file/sheet name.

    Format: {cleaned_file}_{cleaned_sheet}_{4-char-uuid}
    Examples:
        "6月销售报表.xlsx" → "6_e_8_a3f1"
        "sales.xlsx" Sheet "Q1" → "sales_q1_b7c2"
        "customers.csv" → "customers_d4e5"
    """
    import uuid

    # Remove extension
    base = file_name.rsplit(".", 1)[0] if "." in file_name else file_name

    # Clean: keep alphanumeric + Chinese
    cleaned = re.sub(r"[^\w一-鿿]", "_", base)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
    if not cleaned:
        cleaned = "data"

    # Add sheet name if provided
    if sheet_name:
        sheet_cleaned = re.sub(r"[^\w一-鿿]", "_", sheet_name)
        sheet_cleaned = re.sub(r"_+", "_", sheet_cleaned).strip("_").lower()
        if sheet_cleaned:
            cleaned = f"{cleaned}_{sheet_cleaned}"

    # Add 4-char UUID suffix for uniqueness
    suffix = uuid.uuid4().hex[:4]
    return f"{cleaned}_{suffix}"
