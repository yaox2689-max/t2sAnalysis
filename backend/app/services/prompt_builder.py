"""PromptBuilder — Catalog → PromptContext → Markdown.

Assembles the Schema Context section of the SQL generation prompt.
Decoupled from SQLGenerator — change prompt format here, not in the generator.

Usage:
    from app.services.prompt_builder import PromptBuilder

    builder = PromptBuilder()
    context = builder.build_context(catalog)
    markdown = builder.render(context)
"""

from dataclasses import dataclass, field
from typing import Optional

from app.services.dataset_registry import Catalog, ColumnSchema, TableSchema


@dataclass
class PromptContext:
    """Structured prompt input, assembled from Catalog."""
    schema: str                             # Formatted schema + profile text
    examples: list[str] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# Default SQL generation prompt template
_DEFAULT_TEMPLATE = """你是一个数据分析专家。根据用户的问题和数据库 Schema，生成正确的 SQL 查询。

## 数据库 Schema

{schema}

## 规则

1. 只生成 SELECT 查询，禁止 INSERT/UPDATE/DELETE/DROP
2. 使用反引号包裹中文列名：`销售额`
3. 结果集不超过 500 行（自动添加 LIMIT）
4. 使用聚合函数时必须 GROUP BY
5. 优先使用语义类型来判断：measure 列可以 SUM/AVG，dimension 列可以 GROUP BY
{business_rules}

## 输出格式

```json
{{
    "sql": "SELECT ...",
    "explanation": "中文解释查询逻辑"
}}
```"""


class PromptBuilder:
    """Assemble SQL generation prompts from Catalog."""

    def __init__(self, template: Optional[str] = None, duckdb_engine: object = None) -> None:
        self._template = template or _DEFAULT_TEMPLATE
        self._engine = duckdb_engine

    def build_context(self, catalog: Catalog) -> PromptContext:
        """Catalog → PromptContext (structured)."""
        schema_parts = []

        for table in catalog.tables:
            schema_parts.append(self._format_table(table))

        return PromptContext(
            schema="\n\n".join(schema_parts),
            metadata={"table_count": len(catalog.tables)},
        )

    def render(self, context: PromptContext) -> str:
        """PromptContext → final prompt text."""
        business_rules = ""
        if context.business_rules:
            business_rules = "\n".join(f"- {r}" for r in context.business_rules)

        return self._template.format(
            schema=context.schema,
            business_rules=business_rules,
        )

    def build_prompt(self, catalog: Catalog) -> str:
        """Convenience: Catalog → final prompt text in one call."""
        context = self.build_context(catalog)
        return self.render(context)

    def _format_table(self, table: TableSchema) -> str:
        """Format a single table's schema + profile."""
        lines = []

        # Table header
        source_label = self._source_label(table.source_type)
        lines.append(f"### Table: {table.table_name}")
        if table.display_name != table.table_name:
            lines.append(f"来源: {table.display_name} ({source_label})")
        else:
            lines.append(f"来源: {source_label}")
        if table.row_count > 0:
            lines.append(f"行数: {table.row_count:,}")

        # Columns
        lines.append("")
        lines.append("Columns:")
        for col in table.columns:
            lines.append(self._format_column(col))

        # Sample rows (critical for LLM to understand column semantics)
        sample_rows = self._fetch_sample_rows(table.table_name)
        if sample_rows:
            lines.append("")
            lines.append("Sample data (first 3 rows):")
            for row in sample_rows:
                vals = ", ".join(f"{k}={v}" for k, v in row.items() if v is not None)
                lines.append(f"  {vals}")

        return "\n".join(lines)

    def _format_column(self, col: ColumnSchema) -> str:
        """Format a single column's schema + profile."""
        # Show original name if it differs from cleaned name
        display_name = col.name
        if col.original_name and col.original_name != col.name:
            display_name = f"{col.name} (原始列名: {col.original_name})"

        parts = [f"- {display_name} ({col.data_type}, {col.semantic_type})"]

        # Stats line
        stats = []
        if col.unique_count > 0:
            stats.append(f"{col.unique_count} unique")
        if col.null_ratio > 0:
            stats.append(f"{col.null_ratio:.0%} NULL")
        if col.min_value and col.max_value:
            stats.append(f"range: {col.min_value}~{col.max_value}")
        if stats:
            parts[0] += " — " + ", ".join(stats)

        # Example values
        if col.top_values:
            examples = ", ".join(str(v) for v in col.top_values[:5])
            parts.append(f"  Examples: {examples}")

        return "\n".join(parts)

    def _fetch_sample_rows(self, table_name: str) -> list[dict]:
        """Fetch first 3 rows from DuckDB for the prompt."""
        if self._engine is None:
            return []
        try:
            result = self._engine.execute(f'SELECT * FROM "{table_name}" LIMIT 3').fetchdf()
            return result.to_dict("records")
        except Exception:
            return []

    @staticmethod
    def _source_label(source_type: str) -> str:
        """Human-readable source type label."""
        labels = {
            "demo": "内置 Demo 数据",
            "excel": "Excel 上传",
            "csv": "CSV 上传",
        }
        return labels.get(source_type, source_type)
