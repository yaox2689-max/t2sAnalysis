"""清理 DuckDB 中的重复表。

保留每种报表的最新一张，删除同名重复表。

用法：
    1. 先停掉 uvicorn
    2. cd backend && python scripts/cleanup_duplicates.py
"""

import sys
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "analysis.duckdb"


def cleanup():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = duckdb.connect(str(DB_PATH), read_only=False)
    tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
    print(f"Total tables: {len(tables)}")

    # Group tables by base name (remove last _XXXX suffix)
    from collections import defaultdict
    groups: dict[str, list[str]] = defaultdict(list)
    for name in tables:
        # Pattern: {base_name}_{4-char-hex-suffix}
        parts = name.rsplit("_", 1)
        if len(parts) == 2 and len(parts[1]) == 4:
            groups[parts[0]].append(name)
        else:
            groups[name].append(name)

    to_drop = []
    for base, members in groups.items():
        if len(members) > 1:
            # Keep the last one alphabetically (newest by UUID)
            members.sort()
            keep = members[-1]
            drop = members[:-1]
            print(f"\n{base} ({len(members)} copies, keeping {keep}):")
            for d in drop:
                print(f"  DROP {d}")
                to_drop.append(d)

    if not to_drop:
        print("\nNo duplicates found.")
        conn.close()
        return

    print(f"\nDropping {len(to_drop)} duplicate tables...")
    for table in to_drop:
        safe = table.replace('"', '""')
        conn.execute(f'DROP TABLE IF EXISTS "{safe}"')
        print(f"  Dropped: {table}")

    remaining = conn.execute("SHOW TABLES").fetchall()
    print(f"\nDone. {len(remaining)} tables remaining.")

    # Also clean up MySQL datasets table
    print("\nNote: Also run this in MySQL to clean dataset metadata:")
    print("  DELETE FROM datasets WHERE table_name IN (...dropped tables...);")

    conn.close()


if __name__ == "__main__":
    cleanup()
