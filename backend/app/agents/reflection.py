"""Reflection Loop — error classification, SQL fix, schema re-retrieval, and retry orchestration.

This module implements a structured retry loop for the SQL generation pipeline:

1. **ErrorClassifier** — uses LLM to classify errors into schema_error / syntax_error / ambiguous / other
2. **SchemaErrorHandler** — re-retrieves schema context and re-generates SQL
3. **SyntaxErrorHandler** — uses LLM to directly fix malformed SQL
4. **ReflectionLoop** — orchestrates up to *max_retries* attempts

Usage:
    from app.agents.reflection import ReflectionLoop

    loop = ReflectionLoop(
        api_key="...", model="deepseek-chat",
        sql_generator=gen, schema_retriever=retriever,
    )
    result = await loop.run(question, sql, error, task_plan, schema_context)
"""

import json
from typing import Optional

from openai import AsyncOpenAI

from app.core.prompt_loader import prompt_loader
from app.models.task import GeneratedSQL, SchemaContext, TaskPlan


# ── Models ──────────────────────────────────────────────


class ErrorClassification:
    """Result of error type classification."""

    def __init__(
        self,
        error_type: str,
        confidence: float = 0.0,
        detail: str = "",
    ) -> None:
        self.error_type = error_type
        self.confidence = confidence
        self.detail = detail


class ReflectionStep:
    """One attempt recorded during the reflection loop."""

    def __init__(
        self,
        attempt: int,
        error_type: str,
        sql_attempted: str,
        error_message: str = "",
    ) -> None:
        self.attempt = attempt
        self.error_type = error_type
        self.sql_attempted = sql_attempted
        self.error_message = error_message


class ReflectionResult:
    """Final result of the reflection loop.

    *next_action* tells the LangGraph Workflow what to do next:
    - ``retry_generate`` — re-run SQL generation (for syntax/ambiguous errors)
    - ``retry_retrieve`` — re-retrieve schema + re-generate (for schema errors)
    - ``stop`` — give up, return current state
    """

    def __init__(
        self,
        success: bool,
        final_sql: str = "",
        next_action: str = "stop",
        attempts: Optional[list[ReflectionStep]] = None,
    ) -> None:
        self.success = success
        self.final_sql = final_sql
        self.next_action = next_action
        self.attempts = attempts or []


# ── Error Classifier ────────────────────────────────────


class ErrorClassifier:
    """Classify SQL errors using LLM."""

    def __init__(self, llm_client: AsyncOpenAI, model: str) -> None:
        self._client = llm_client
        self._model = model
        self._prompt = prompt_loader.load("reflection/error_classifier")

    async def classify(self, error_msg: str) -> ErrorClassification:
        """Classify an error message into a known type."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._prompt},
                {"role": "user", "content": f"## Error Message\n\n{error_msg}"},
            ],
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""
        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> ErrorClassification:
        """Parse LLM response into ErrorClassification."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return ErrorClassification("other", 0.0, "Failed to parse classifier response")

        return ErrorClassification(
            error_type=data.get("error_type", "other"),
            confidence=data.get("confidence", 0.0),
            detail=data.get("detail", ""),
        )


# ── Reflection Loop ─────────────────────────────────────


class ReflectionLoop:
    """Orchestrate the retry loop for failed SQL generation or execution."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str],
        sql_generator: object,
        schema_retriever: object,
        http_client: Optional[object] = None,
    ) -> None:
        kwargs = {"api_key": api_key, "base_url": base_url}
        if http_client is not None:
            kwargs["http_client"] = http_client
        self._client = AsyncOpenAI(**kwargs)
        self._model = model
        self._sql_generator = sql_generator
        self._schema_retriever = schema_retriever
        self._classifier = ErrorClassifier(self._client, model)
        self._fix_prompt = prompt_loader.load("reflection/sql_fix")

    async def run(
        self,
        question: str,
        sql: str,
        error_message: str,
        task_plan: TaskPlan,
        schema_context: SchemaContext,
        max_retries: int = 3,
    ) -> ReflectionResult:
        """Run the reflection loop until success or retries exhausted.

        Each iteration: classify error → apply handler → check validity.
        """
        attempts: list[ReflectionStep] = []
        current_sql = sql
        current_error = error_message
        current_context = schema_context

        for i in range(1, max_retries + 1):
            classification = await self._classifier.classify(current_error)
            attempts.append(
                ReflectionStep(
                    attempt=i,
                    error_type=classification.error_type,
                    sql_attempted=current_sql,
                    error_message=current_error,
                )
            )

            if classification.error_type == "other":
                break

            gen_result: Optional[GeneratedSQL] = None
            try:
                gen_result = await self._apply_handler(
                    classification.error_type,
                    question,
                    current_sql,
                    current_error,
                    task_plan,
                    current_context,
                )
            except Exception as exc:
                current_error = str(exc)
                continue

            if gen_result is not None and gen_result.valid:
                return ReflectionResult(
                    success=True,
                    final_sql=gen_result.sql,
                    next_action="stop",
                    attempts=attempts,
                )

            current_sql = gen_result.sql if gen_result else current_sql
            current_error = gen_result.explanation if gen_result else current_error

        # Determine what the graph should do next
        next_action = self._resolve_next_action(attempts)
        return ReflectionResult(
            success=False,
            final_sql=current_sql,
            next_action=next_action,
            attempts=attempts,
        )

    @staticmethod
    def _resolve_next_action(attempts: list[ReflectionStep]) -> str:
        """Resolve the next_action based on the last error type.

        Tells the LangGraph Workflow what to do:
        - ``retry_retrieve`` → schema was wrong, re-retrieve + re-generate
        - ``retry_generate`` → SQL was wrong, re-generate only
        - ``stop`` → give up
        """
        if not attempts:
            return "stop"
        last = attempts[-1].error_type
        if last == "schema_error":
            return "retry_retrieve"
        if last in ("syntax_error", "ambiguous"):
            return "retry_generate"
        return "stop"

    # ── Handlers ─────────────────────────────────────────

    async def _apply_handler(
        self,
        error_type: str,
        question: str,
        sql: str,
        error_message: str,
        task_plan: TaskPlan,
        schema_context: SchemaContext,
    ) -> Optional[GeneratedSQL]:
        """Route to the appropriate handler based on error type."""
        if error_type == "schema_error":
            return await self._handle_schema_error(question, task_plan, schema_context)
        if error_type == "syntax_error":
            return await self._handle_syntax_error(sql, error_message)
        if error_type == "ambiguous":
            return await self._handle_ambiguous(question, task_plan, schema_context)
        return None

    async def _handle_schema_error(
        self,
        question: str,
        task_plan: TaskPlan,
        _original_context: SchemaContext,
    ) -> GeneratedSQL:
        """Re-retrieve schema with broader search and re-generate SQL."""
        new_context = await self._schema_retriever.retrieve(  # type: ignore[union-attr]
            question, top_k_tables=5, top_k_columns=10,
        )
        return await self._sql_generator.generate(task_plan, new_context)  # type: ignore[union-attr]

    async def _handle_syntax_error(
        self,
        sql: str,
        error_message: str,
    ) -> GeneratedSQL:
        """Use LLM to directly fix a syntax error in SQL."""
        user_msg = (
            f"## Original SQL\n\n{sql}\n\n"
            f"## Error Message\n\n{error_message}"
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._fix_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
        )
        raw = response.choices[0].message.content or ""
        return self._parse_fix(raw)

    async def _handle_ambiguous(
        self,
        question: str,
        task_plan: TaskPlan,
        schema_context: SchemaContext,
    ) -> GeneratedSQL:
        """Re-generate SQL with more explicit context instructions."""
        return await self._sql_generator.generate(task_plan, schema_context)  # type: ignore[union-attr]

    @staticmethod
    def _parse_fix(raw: str) -> GeneratedSQL:
        """Parse LLM fix response into GeneratedSQL."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return GeneratedSQL(
                sql="",
                explanation="Failed to parse fix response as JSON",
                valid=False,
            )

        sql = data.get("sql", "")
        return GeneratedSQL(
            sql=sql,
            explanation=data.get("explanation", ""),
            valid=data.get("valid", True),
        )
