"""Tests for column_cleaner — cleaning, deduplication, table name generation."""


from app.tools.column_cleaner import (
    clean_column_name,
    clean_column_names,
    generate_table_name,
)

# ── clean_column_name tests ───────────────────────────────


class TestCleanColumnName:
    def test_chinese_preserved(self):
        """Chinese characters should be preserved."""
        seen: set[str] = set()
        result = clean_column_name("销售额", 0, seen)
        assert result == "销售额"

    def test_english_lowercased(self):
        """English names are lowercased."""
        seen: set[str] = set()
        result = clean_column_name("Sales Amount", 0, seen)
        assert result == "sales_amount"

    def test_special_chars_removed(self):
        """Special characters are replaced with underscores."""
        seen: set[str] = set()
        result = clean_column_name("revenue@2024!", 0, seen)
        assert "@" not in result
        assert "!" not in result

    def test_leading_digit_prefixed(self):
        """Names starting with a digit get 'n_' prefix."""
        seen: set[str] = set()
        result = clean_column_name("123abc", 0, seen)
        assert result == "n_123abc"

    def test_year_prefix(self):
        """Names containing '年' and starting with a digit get 'year_' prefix."""
        seen: set[str] = set()
        result = clean_column_name("2024年", 0, seen)
        assert result.startswith("year_")

    def test_empty_name_fallback(self):
        """Empty name uses index-based fallback."""
        seen: set[str] = set()
        result = clean_column_name("", 2, seen)
        assert result == "col_3"

    def test_whitespace_only_fallback(self):
        """Whitespace-only name uses fallback."""
        seen: set[str] = set()
        result = clean_column_name("   ", 5, seen)
        assert result == "col_6"

    def test_consecutive_underscores_collapsed(self):
        """Multiple consecutive underscores are collapsed."""
        seen: set[str] = set()
        result = clean_column_name("a---b___c", 0, seen)
        assert "__" not in result


# ── Deduplication ─────────────────────────────────────────


class TestDeduplication:
    def test_duplicate_names_get_suffix(self):
        """Duplicate column names get _2, _3 etc."""
        seen: set[str] = set()
        r1 = clean_column_name("name", 0, seen)
        r2 = clean_column_name("name", 1, seen)
        assert r1 == "name"
        assert r2 == "name_2"

    def test_triple_duplicates(self):
        """Three identical names produce name, name_2, name_3."""
        seen: set[str] = set()
        r1 = clean_column_name("x", 0, seen)
        r2 = clean_column_name("x", 1, seen)
        r3 = clean_column_name("x", 2, seen)
        assert r1 == "x"
        assert r2 == "x_2"
        assert r3 == "x_3"


# ── clean_column_names (list) ─────────────────────────────


class TestCleanColumnNames:
    def test_mixed_names(self):
        """Full list cleaning with mixed types."""
        result = clean_column_names(["ID", "Name", "", "Sales_Amount"])
        assert result == ["id", "name", "col_3", "sales_amount"]

    def test_chinese_and_english(self):
        """Mix of Chinese and English columns."""
        result = clean_column_names(["销售额", "Date", "数量"])
        assert result == ["销售额", "date", "数量"]


# ── generate_table_name ───────────────────────────────────


class TestGenerateTableName:
    def test_simple_csv(self):
        """Simple CSV file generates expected format."""
        name = generate_table_name("customers.csv")
        assert name.startswith("customers_")
        # Should end with 4-char hex suffix
        suffix = name.split("_")[-1]
        assert len(suffix) == 4
        assert all(c in "0123456789abcdef" for c in suffix)

    def test_excel_with_sheet(self):
        """Excel file with sheet name includes both in table name."""
        name = generate_table_name("sales.xlsx", sheet_name="Q1")
        assert "sales" in name
        assert "q1" in name

    def test_chinese_filename(self):
        """Chinese characters in filename are preserved."""
        name = generate_table_name("6月销售报表.xlsx")
        assert "6" in name

    def test_no_extension(self):
        """File without extension still works."""
        name = generate_table_name("data_table")
        assert name.startswith("data_table_")

    def test_unique_names(self):
        """Two calls produce different names (UUID suffix)."""
        name1 = generate_table_name("data.csv")
        name2 = generate_table_name("data.csv")
        assert name1 != name2
