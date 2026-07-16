"""SQL Generator — turns TaskPlan + SchemaContext into a GeneratedSQL.

This is a pure LLM call with structured output. It does NOT:
- execute SQL
- validate SQL beyond parse-level syntax checking
- query the database
- integrate with TaskAnalyzer, Validator, or Executor

Usage:
    from app.agents.sql_generator import SQLGenerator

    gen = SQLGenerator(api_key="...", model="deepseek-chat")
    result = await gen.generate(task_plan, schema_context)
"""

import json
from typing import Optional

import sqlglot
from openai import AsyncOpenAI

from app.core.prompt_loader import prompt_loader
from app.models.task import GeneratedSQL, SchemaContext, TaskPlan


def _build_schema_text(schema: SchemaContext) -> str:
    """Format SchemaContext into a human-readable prompt block."""
    lines = []
    for table in schema.tables:
        col_lines = schema.columns.get(table, [])
        cols = "\n    ".join(
            f"- {c.get('column_name', '?')} ({c.get('data_type', '?')})"
            for c in col_lines
        )
        lines.append(f"Table: {table}\n    Columns:\n    {cols}")

        sample = schema.sample_rows.get(table)
        if sample:
            sample_lines = "\n    ".join(str(r) for r in sample[:3])
            lines.append(f"    Sample rows:\n    {sample_lines}")

    if schema.relationships:
        lines.append("\nRelationships:")
        for rel in schema.relationships:
            lines.append(f"  - {rel}")

    return "\n\n".join(lines)


def _check_schema_valid(sql: str, schema: SchemaContext) -> bool:
    """Verify generated SQL only references tables from SchemaContext."""
    try:
        tree = sqlglot.parse_one(sql)
    except sqlglot.errors.ParseError:
        return True  # let downstream parse error handle it

    all_tables = set(schema.tables)

    for node in tree.walk():
        if isinstance(node, sqlglot.expressions.Table):
            name = node.name
            if name not in all_tables:
                return False
    return True


class SQLGenerator:
    """Generates SQL from a TaskPlan + SchemaContext using LLM."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self._system_prompt = prompt_loader.load("sql_agent/sql_generation")

    async def generate(
        self,
        task_plan: TaskPlan,
        schema_context: SchemaContext,
    ) -> GeneratedSQL:
        """Generate a SQL statement from a structured task plan."""
        schema_text = _build_schema_text(schema_context)

        user_prompt = (
            f"## Task Plan\n\n"
            f"Task Type: {task_plan.task_type}\n"
            f"Metrics: {', '.join(task_plan.metrics)}\n"
            f"Dimensions: {', '.join(task_plan.dimensions)}\n"
            f"Time Range: {task_plan.time_range}\n\n"
            f"## Schema Context\n\n{schema_text}"
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content or ""
        return self._parse(raw, schema_context)

    def _parse(self, raw: str, schema: SchemaContext) -> GeneratedSQL:
        """Parse LLM response into GeneratedSQL.

        Checks schema validity — if the SQL references tables not in
        the provided SchemaContext, it is marked invalid.
        """
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return GeneratedSQL(
                sql="",
                explanation="Failed to parse LLM response as JSON",
                valid=False,
            )

        sql = data.get("sql", "")

        # Parse-level check
        try:
            sqlglot.parse_one(sql)
        except sqlglot.errors.ParseError as e:
            return GeneratedSQL(
                sql=sql,
                explanation=f"Generated SQL has syntax errors: {e}",
                valid=False,
            )

        # Schema-scope check — only tables from SchemaContext
        if not _check_schema_valid(sql, schema):
            return GeneratedSQL(
                sql=sql,
                explanation="Generated SQL references tables not in the provided schema",
                valid=False,
            )

        return GeneratedSQL(
            sql=sql,
            explanation=data.get("explanation", ""),
            valid=data.get("valid", True),
        )
