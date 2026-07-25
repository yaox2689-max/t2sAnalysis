"""SQL safety — shared write-operation blocking for all executors."""

from typing import Optional

import sqlglot
import sqlglot.expressions as exp

# Blocked write operations
_WRITE_OPS = frozenset({
    exp.Insert, exp.Update, exp.Delete,
    exp.Drop, exp.Alter, exp.Create, exp.Grant,
})


def check_write_blocked(sql: str) -> Optional[str]:
    """Check if SQL contains write operations. Returns warning string or None."""
    try:
        tree = sqlglot.parse_one(sql)
    except sqlglot.errors.ParseError:
        return None  # let execution handle the parse error

    for node in tree.walk():
        if isinstance(node, tuple(_WRITE_OPS)):
            return f"WRITE_OPERATION: {node.key.upper()}"
    return None
