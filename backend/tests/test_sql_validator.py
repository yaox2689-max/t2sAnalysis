"""Tests for SQLValidator — write ops, danger patterns, nesting, CTE."""

import pytest

from app.tools.sql_validator import SQLValidator


@pytest.fixture(scope="module")
def validator():
    return SQLValidator()


# ── Normal SELECT ──────────────────────────────────────

class TestNormal:
    def test_simple_select(self, validator):
        r = validator.validate("SELECT id, name FROM orders WHERE id = 1")
        assert r.passed is True
        assert r.risk_level == "low"
        assert r.warnings == []

    def test_select_limit(self, validator):
        r = validator.validate("SELECT * FROM orders LIMIT 10")
        assert r.passed is True
        assert r.warnings == ["FULL_TABLE_SCAN"]

    def test_join(self, validator):
        r = validator.validate(
            "SELECT o.id, p.value FROM orders o "
            "JOIN payments p ON o.id = p.order_id "
            "WHERE o.id = 1"
        )
        assert r.passed is True
        assert r.risk_level == "low"

    def test_group_by(self, validator):
        r = validator.validate(
            "SELECT status, COUNT(*) FROM orders GROUP BY status"
        )
        assert r.passed is True
        assert r.warnings == ["FULL_TABLE_SCAN"]


# ── Write operations ──────────────────────────────────

class TestWriteBlock:
    def test_drop(self, validator):
        r = validator.validate("DROP TABLE orders")
        assert r.passed is False
        assert r.risk_level == "high"

    def test_delete(self, validator):
        r = validator.validate("DELETE FROM orders WHERE id = 1")
        assert r.passed is False

    def test_insert(self, validator):
        r = validator.validate("INSERT INTO orders (id) VALUES (1)")
        assert r.passed is False

    def test_update(self, validator):
        r = validator.validate("UPDATE orders SET status = 'x' WHERE id = 1")
        assert r.passed is False

    def test_alter(self, validator):
        r = validator.validate("ALTER TABLE orders ADD COLUMN x INT")
        assert r.passed is False

    def test_create(self, validator):
        r = validator.validate("CREATE TABLE x (id INT)")
        assert r.passed is False

    def test_grant(self, validator):
        r = validator.validate("GRANT SELECT ON orders TO user")
        assert r.passed is False


# ── Nested / CTE attacks ──────────────────────────────

class TestNestedWrite:
    def test_subquery_delete(self, validator):
        r = validator.validate(
            "WITH deleted AS (DELETE FROM orders WHERE id = 1) "
            "SELECT * FROM deleted"
        )
        assert r.passed is False
        assert "WRITE_OPERATION" in r.warnings[0]

    def test_cte_with_update(self, validator):
        r = validator.validate(
            "WITH x AS (UPDATE orders SET status = 'x') "
            "SELECT * FROM x"
        )
        assert r.passed is False
        assert "WRITE_OPERATION" in r.warnings[0]

    def test_cte_with_delete(self, validator):
        r = validator.validate(
            "WITH deleted AS (DELETE FROM orders WHERE id = 1) "
            "SELECT * FROM deleted"
        )
        assert r.passed is False

    def test_nested_insert_subquery(self, validator):
        r = validator.validate(
            "SELECT * FROM (SELECT * FROM (INSERT INTO t VALUES (1)) AS y) AS x"
        )
        assert r.passed is False


# ── Danger patterns ───────────────────────────────────

class TestDangerPatterns:
    def test_cross_join(self, validator):
        r = validator.validate(
            "SELECT * FROM orders CROSS JOIN payments"
        )
        assert r.passed is True
        assert "CROSS_JOIN" in r.warnings

    def test_left_fuzzy_like(self, validator):
        r = validator.validate(
            "SELECT * FROM orders WHERE name LIKE '%abc'"
        )
        assert r.passed is True
        assert "LEFT_FUZZY_LIKE" in r.warnings

    def test_order_by_rand(self, validator):
        r = validator.validate(
            "SELECT * FROM orders ORDER BY RAND()"
        )
        assert r.passed is True
        assert "ORDER_BY_RAND" in r.warnings

    def test_multiple_warnings(self, validator):
        r = validator.validate(
            "SELECT * FROM orders CROSS JOIN payments ORDER BY RAND()"
        )
        assert r.passed is True
        # Should contain both CROSS_JOIN and ORDER_BY_RAND
        assert len(r.warnings) >= 2


# ── Parse errors ──────────────────────────────────────

class TestParseError:
    def test_invalid_syntax(self, validator):
        r = validator.validate("SELECT FROM WHERE")
        assert r.passed is False
        assert r.risk_level == "high"
        assert "PARSE_ERROR" in r.warnings[0]
