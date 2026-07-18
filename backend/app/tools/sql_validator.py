"""SQL static analysis using sqlglot AST.

Safety validator for the Agent pipeline.  Analyses SQL statements
before execution and reports:

- Write operations (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT)
- Dangerous patterns (full-table scan, CROSS JOIN, left-fuzzy LIKE, ORDER BY RAND())

This is the first layer of defence.  It does NOT execute or modify SQL.
The caller (Agent workflow) decides whether to proceed based on the result.

Usage:
    from app.tools.sql_validator import SQLValidator

    v = SQLValidator()
    result = v.validate("SELECT * FROM orders WHERE id = 1")
    assert result.passed is True
"""

from typing import Optional

import sqlglot
import sqlglot.expressions as exp
from sqlglot import parse_one


# ── Blocked write statement types ──────────────────────
_WRITE_OPS = frozenset({
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Grant,
})


class RiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValidationResult:
    """Describes the outcome of a SQL validation check.

    The caller (Agent workflow) decides whether to proceed.
    This class only reports findings, it does NOT block execution.
    """

    def __init__(
        self,
        passed: bool,
        risk_level: str = RiskLevel.LOW,
        warnings: Optional[list[str]] = None,
    ) -> None:
        self.passed = passed
        self.risk_level = risk_level
        self.warnings = warnings or []

    def __repr__(self) -> str:
        return (
            f"ValidationResult(passed={self.passed}, "
            f"risk_level='{self.risk_level}', "
            f"warnings={self.warnings})"
        )


class SQLValidator:
    """sqlglot-based SQL safety validator."""

    def validate(self, sql: str) -> ValidationResult:
        """Analyse a SQL statement and return a validation result."""
        try:
            tree = parse_one(sql, dialect="mysql")
        except sqlglot.errors.ParseError as e:
            return ValidationResult(
                passed=False,
                risk_level=RiskLevel.HIGH,
                warnings=[f"PARSE_ERROR: {e}"],
            )

        warnings: list[str] = []

        # ── Scan all nodes for write operations ──────────
        for node in tree.walk():
            if isinstance(node, tuple(_WRITE_OPS)):
                return ValidationResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    warnings=[f"WRITE_OPERATION: {node.key.upper()}"],
                )

        # ── Scan for dangerous patterns ──────────────────
        for node in tree.walk():
            if isinstance(node, exp.Select):
                if not node.args.get("where") and node.args.get("from_"):
                    warnings.append("FULL_TABLE_SCAN")
                    break

        # Cross join detection — look for Join nodes with side="RIGHT" or kind="CROSS"
        from sqlglot.expressions import Join
        for node in tree.walk():
            if isinstance(node, Join):
                if node.kind and node.kind.upper() == "CROSS":
                    warnings.append("CROSS_JOIN")
                    break

        for node in tree.walk():
            if isinstance(node, exp.Like):
                right = node.find(exp.Literal)
                if right and isinstance(right, exp.Literal):
                    if right.this.startswith("%"):
                        warnings.append("LEFT_FUZZY_LIKE")
                        break

        for node in tree.walk():
            if isinstance(node, exp.Order):
                for expr in node.expressions:
                    if isinstance(expr, exp.Ordered) and isinstance(expr.this, exp.Rand):
                        warnings.append("ORDER_BY_RAND")
                        break

        risk_level = RiskLevel.MEDIUM if warnings else RiskLevel.LOW

        return ValidationResult(
            passed=True,
            risk_level=risk_level,
            warnings=warnings,
        )
