"""Evidence Analyzer — structured conclusion with evidence chain and limitations.

This tool answers "why" questions about query results by:
1. Comparing primary and comparison data (current vs prior period).
2. Identifying which dimensions contribute most to the observed change.
3. Building an evidence chain ranked by impact.
4. Explicitly stating limitations — what the data cannot explain.

It does NOT:
- infer causation from correlation
- access the database
- generate SQL
- modify workflow state
- call other tools

Usage:
    from app.tools.evidence_analyzer import EvidenceAnalyzer

    analyzer = EvidenceAnalyzer(api_key="...", model="deepseek-chat")
    report = await analyzer.analyze(
        "为什么3月份销量下降",
        primary_result,
        comparison_result,
    )
"""

import json
from typing import Optional

from app.core.prompt_loader import prompt_loader
from app.core.utils import create_llm_client, format_query_result
from app.models.query import QueryResult


def _load_prompt() -> str:
    return prompt_loader.load("tools/evidence_analyzer")


# ── Models ──────────────────────────────────────────────


class EvidenceItem:
    """A single piece of evidence with supporting data."""

    def __init__(
        self,
        claim: str,
        data: Optional[list[str]] = None,
        source: str = "",
        strength: Optional[float] = None,
    ) -> None:
        self.claim = claim
        self.data = data or []
        self.source = source
        self.strength = strength


class EvidenceReport:
    """Structured output of the evidence analysis."""

    def __init__(
        self,
        conclusion: str = "",
        evidence_chain: Optional[list[EvidenceItem]] = None,
        suggestions: Optional[list[str]] = None,
        limitations: Optional[list[str]] = None,
    ) -> None:
        self.conclusion = conclusion
        self.evidence_chain = evidence_chain or []
        self.suggestions = suggestions or []
        self.limitations = limitations or []


# ── Result formatting ───────────────────────────────────


def _format_result(result: QueryResult, label: str = "primary") -> str:
    """Format a QueryResult into a compact text summary."""
    return format_query_result(result, label=label, lang="zh")


# ── Tool ─────────────────────────────────────────────────


class EvidenceAnalyzer:
    """Analyse why a change happened, producing evidence-backed conclusions."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        http_client: Optional[object] = None,
    ) -> None:
        self._client = create_llm_client(api_key, base_url, http_client=http_client)
        self._model = model
        self._prompt = _load_prompt()

    async def analyze(
        self,
        question: str,
        primary_result: QueryResult,
        comparison_result: Optional[QueryResult] = None,
    ) -> EvidenceReport:
        """Analyse query results and produce an evidence report.

        Returns early without an LLM call when primary data is empty.
        """
        if not primary_result.rows:
            return EvidenceReport(
                conclusion="数据不足，无法分析",
                limitations=["主查询结果无数据"],
            )

        user_msg = self._build_prompt(question, primary_result, comparison_result)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        raw = response.choices[0].message.content or ""
        return self._parse(raw)

    def _build_prompt(
        self,
        question: str,
        primary: QueryResult,
        comparison: Optional[QueryResult],
    ) -> str:
        """Build the user message for the LLM."""
        parts = [f"## 问题\n\n{question}"]

        parts.append(
            "## 数据\n\n" + _format_result(primary, label="主数据")
        )
        if comparison and comparison.rows:
            parts.append(_format_result(comparison, label="对比数据"))

        return "\n\n".join(parts)

    @staticmethod
    def _parse(raw: str) -> EvidenceReport:
        """Parse LLM response into an EvidenceReport."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return EvidenceReport(conclusion=raw)

        chain_data = data.get("evidence_chain", [])
        chain = [
            EvidenceItem(
                claim=item.get("claim", ""),
                data=item.get("data", []),
                source=item.get("source", ""),
                strength=item.get("strength"),
            )
            for item in chain_data
        ]

        return EvidenceReport(
            conclusion=data.get("conclusion", ""),
            evidence_chain=chain,
            suggestions=data.get("suggestions", []),
            limitations=data.get("limitations", []),
        )
