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

        # ── Single AST pass for all checks ─────────────────
        has_where = False
        for node in tree.walk():
            # Write operations → immediate failure
            if isinstance(node, tuple(_WRITE_OPS)):
                return ValidationResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    warnings=[f"WRITE_OPERATION: {node.key.upper()}"],
                )
            # Full table scan detection
            if isinstance(node, exp.Select) and node.args.get("from_") and not node.args.get("where"):
                has_where = True
                warnings.append("FULL_TABLE_SCAN")
            # Cross join detection
            if isinstance(node, exp.Join) and node.kind and node.kind.upper() == "CROSS":
                warnings.append("CROSS_JOIN")
            # Left fuzzy LIKE detection
            if isinstance(node, exp.Like):
                right = node.find(exp.Literal)
                if right and isinstance(right, exp.Literal) and right.this.startswith("%"):
                    warnings.append("LEFT_FUZZY_LIKE")
            # ORDER BY RAND() detection
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
