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
import re
from datetime import datetime
from typing import Optional

import sqlglot

from app.core.llm_client import LLMClient
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
        tree = sqlglot.parse_one(sql, dialect="mysql")
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

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client
        self._prompt = prompt_loader.load("sql_agent/sql_generation")

    async def generate(
        self,
        task_plan: TaskPlan,
        schema_context: SchemaContext,
        prompt_text: Optional[str] = None,
        question: Optional[str] = None,
    ) -> GeneratedSQL:
        """Generate a SQL statement from a structured task plan.

        Args:
            task_plan: Structured task description.
            schema_context: Schema info for validation.
            prompt_text: Pre-built prompt from PromptBuilder (new path).
                If None, falls back to legacy _build_schema_text.
            question: The user's original question (for context).
        """
        if prompt_text:
            schema_text = ""  # prompt_text already includes schema
            system_prompt = prompt_text
        else:
            schema_text = _build_schema_text(schema_context)
            system_prompt = self._prompt

        user_prompt = (
            f"## Task Plan\n\n"
            f"Task Type: {task_plan.task_type}\n"
            f"Metrics: {', '.join(task_plan.metrics)}\n"
            f"Dimensions: {', '.join(task_plan.dimensions)}\n"
            f"Time Range: {task_plan.time_range}\n\n"
            f"Today's date is {datetime.now().strftime('%Y-%m-%d')}.\n\n"
        )

        if question:
            user_prompt += f"## User's Original Question\n\n{question}\n\n"

        if schema_text:
            user_prompt += f"## Schema Context\n\n{schema_text}"

        raw = await self._llm_client.call(
            system_prompt=system_prompt,
            user_msg=user_prompt,
            temperature=0.1,
        )
        parsed = self._parse(raw, schema_context)
        return parsed

    def _parse(self, raw: str, schema: SchemaContext) -> GeneratedSQL:
        """Parse LLM response into GeneratedSQL.

        Checks schema validity — if the SQL references tables not in
        the provided SchemaContext, it is marked invalid.
        """
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            # Try extracting JSON from markdown code fence
            m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
            if m:
                try:
                    data = json.loads(m.group(1))
                except (json.JSONDecodeError, TypeError, ValueError):
                    return GeneratedSQL(
                        sql="",
                        explanation="Failed to parse LLM response as JSON",
                        valid=False,
                    )
            else:
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
