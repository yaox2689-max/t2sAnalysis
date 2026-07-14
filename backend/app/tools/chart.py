"""Chart Tool — data-driven chart type detection and ECharts option generation.

This is a pure Python rule engine.  It does NOT:
- call any LLM
- access the database
- read schema information
- modify workflow state

Usage:
    from app.tools.chart import ChartTool

    tool = ChartTool()
    result = tool.render(query_result, task_plan)
    # result.chart_type  → "line" | "bar" | "pie" | "scatter" | "histogram"
    # result.echarts_option → dict ready for JSON serialisation
"""

from typing import Any, Optional

from app.models.query import QueryResult
from app.models.task import TaskPlan


class ChartResult:
    """Output contract for the Chart Tool."""

    def __init__(
        self,
        chart_type: str = "",
        echarts_option: Optional[dict] = None,
        title: Optional[str] = None,
        x_field: Optional[str] = None,
        y_field: Optional[str] = None,
        supported: bool = True,
    ) -> None:
        self.chart_type = chart_type
        self.echarts_option = echarts_option or {}
        self.title = title
        self.x_field = x_field
        self.y_field = y_field
        self.supported = supported


# ── Field heuristics — keep these lists in one place ─────

_TIME_KEYWORDS = frozenset({
    "date", "time", "timestamp", "datetime",
    "year", "month", "day", "hour", "minute",
    "created_at", "updated_at", "purchase_date",
    "order_date", "shipping_date", "delivery_date",
})

_CATEGORY_KEYWORDS = frozenset({
    "category", "name", "status", "type", "class",
    "city", "state", "country", "region", "group",
    "product_category", "product_name", "customer_city",
    "payment_type", "review_score",
})

_NUMERIC_TYPES = frozenset({
    "int", "integer", "bigint", "smallint", "tinyint",
    "decimal", "numeric", "float", "double", "real",
})

_NUMERIC_KEYWORDS = frozenset({
    "price", "amount", "total", "sales", "revenue", "income",
    "count", "quantity", "sum", "avg", "average", "rate",
    "score", "value", "weight", "height", "length", "width",
    "cost", "profit", "discount", "tax", "fee",
    "payment_value", "price", "freight_value",
})


def _column_type(col: dict) -> str:
    return (col.get("data_type") or col.get("type") or "").lower()


def _is_numeric(col: dict) -> bool:
    name = (col.get("column_name") or col.get("name") or "").lower()
    t = _column_type(col)
    if t in _NUMERIC_TYPES or any(kw in t for kw in ("int", "dec", "num", "float", "double")):
        return True
    return any(kw in name for kw in _NUMERIC_KEYWORDS)


def _is_time(col: dict) -> bool:
    name = (col.get("column_name") or col.get("name") or "").lower()
    t = _column_type(col)
    if t in ("date", "datetime", "timestamp", "year"):
        return True
    return any(kw in name for kw in _TIME_KEYWORDS)


def _is_category(col: dict) -> bool:
    name = (col.get("column_name") or col.get("name") or "").lower()
    return any(kw in name for kw in _CATEGORY_KEYWORDS)


def _field_name(col: dict) -> str:
    return col.get("column_name") or col.get("name") or ""


# ── Column classification ───────────────────────────────


def _classify_columns(columns: list[dict]) -> dict:
    """Sort columns into time / category / numeric buckets."""
    time_cols: list[str] = []
    cat_cols: list[str] = []
    num_cols: list[str] = []

    for col in columns:
        if _is_time(col):
            time_cols.append(_field_name(col))
        elif _is_numeric(col):
            num_cols.append(_field_name(col))
        elif _is_category(col):
            cat_cols.append(_field_name(col))

    # Fallback: if nothing was classified, treat leftmost as category
    if not time_cols and not cat_cols and not num_cols and columns:
        cat_cols.append(_field_name(columns[0]))

    return {"time": time_cols, "category": cat_cols, "numeric": num_cols}


# ── Chart type detection ────────────────────────────────


def detect_chart_type(
    columns: list[dict],
    rows: list[dict],
    task_plan: Optional[TaskPlan] = None,
) -> str:
    """Determine the best chart type for the given data.

    Priority:
    1. ``task_plan.chart_type_hint`` if set and compatible.
    2. Rule-based inference from column types and row count.
    """
    # 1. Respect hint from TaskPlan
    hint = task_plan and task_plan.chart_type_hint
    if hint and hint in ("line", "bar", "pie", "scatter", "histogram"):
        return hint

    # 2. Empty or single-row data → no chart
    if not rows or len(rows) < 2:
        return "none"

    classes = _classify_columns(columns)

    # 3. Time + numeric → Line
    if classes["time"] and classes["numeric"]:
        return "line"

    # 4. Two numeric columns → Scatter
    if len(classes["numeric"]) >= 2:
        return "scatter"

    # 5. Single numeric column → Histogram
    if classes["numeric"] and not classes["category"]:
        return "histogram"

    # 6. Category + numeric → Bar (default for comparisons)
    if classes["category"] and classes["numeric"]:
        num_count = len(classes["numeric"])
        cat_count = len(classes["category"])
        # Few categories, one numeric → check distinct values for Pie
        if cat_count == 1 and num_count == 1 and len(rows) <= 12:
            return "pie"
        return "bar"

    # 7. Fallback
    return "bar"


# ── ECharts option builders ─────────────────────────────


def _build_line_option(
    columns: list[dict],
    rows: list[dict],
    col_classes: dict,
) -> dict:
    x_field = (col_classes["time"] or col_classes["category"] or [_field_name(columns[0])])[0]
    y_fields = col_classes["numeric"] or [_field_name(columns[-1])]

    series = []
    for yf in y_fields:
        series.append({
            "name": yf,
            "type": "line",
            "data": [float(r.get(yf, 0) or 0) for r in rows],
            "smooth": True,
        })

    return {
        "title": {"text": ""},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": y_fields} if len(y_fields) > 1 else {},
        "xAxis": {
            "type": "category",
            "data": [str(r.get(x_field, "")) for r in rows],
            "axisLabel": {"rotate": 45} if len(rows) > 10 else {},
        },
        "yAxis": {"type": "value"},
        "series": series,
        "grid": {"left": 60, "right": 30, "bottom": 60},
    }


def _build_bar_option(
    columns: list[dict],
    rows: list[dict],
    col_classes: dict,
) -> dict:
    x_field = (col_classes["category"] or col_classes["time"] or [_field_name(columns[0])])[0]
    y_fields = col_classes["numeric"] or [_field_name(columns[-1])]

    series = []
    for yf in y_fields:
        series.append({
            "name": yf,
            "type": "bar",
            "data": [float(r.get(yf, 0) or 0) for r in rows],
        })

    return {
        "title": {"text": ""},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": y_fields} if len(y_fields) > 1 else {},
        "xAxis": {
            "type": "category",
            "data": [str(r.get(x_field, "")) for r in rows],
            "axisLabel": {"rotate": 45} if len(rows) > 10 else {},
        },
        "yAxis": {"type": "value"},
        "series": series,
        "grid": {"left": 60, "right": 30, "bottom": 60},
    }


def _build_pie_option(columns: list[dict], rows: list[dict], col_classes: dict) -> dict:
    cat_field = col_classes["category"][0] if col_classes["category"] else _field_name(columns[0])
    num_field = col_classes["numeric"][0] if col_classes["numeric"] else _field_name(columns[-1])

    return {
        "title": {"text": "", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "series": [{
            "type": "pie",
            "radius": ["0%", "70%"],
            "data": [
                {"name": str(r.get(cat_field, "")), "value": float(r.get(num_field, 0) or 0)}
                for r in rows
            ],
            "emphasis": {
                "itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0,0,0,0.5)"}
            },
        }],
    }


def _build_scatter_option(columns: list[dict], rows: list[dict], col_classes: dict) -> dict:
    nums = col_classes["numeric"]
    x_field = nums[0]
    y_field = nums[1] if len(nums) > 1 else _field_name(columns[-1])

    return {
        "tooltip": {"trigger": "item"},
        "xAxis": {
            "type": "value",
            "name": x_field,
        },
        "yAxis": {
            "type": "value",
            "name": y_field,
        },
        "series": [{
            "type": "scatter",
            "data": [[float(r.get(x_field, 0) or 0), float(r.get(y_field, 0) or 0)] for r in rows],
        }],
        "grid": {"left": 60, "right": 30, "bottom": 60},
    }


def _build_histogram_option(columns: list[dict], rows: list[dict], col_classes: dict) -> dict:
    num_field = col_classes["numeric"][0] if col_classes["numeric"] else _field_name(columns[-1])
    values = sorted(float(r.get(num_field, 0) or 0) for r in rows)

    # Simple binning: sqrt(n) bins
    import math
    n = len(values)
    bin_count = max(5, min(30, int(math.sqrt(n))))
    min_v, max_v = values[0], values[-1]
    if max_v == min_v:
        bins = [min_v]
        counts = [n]
    else:
        bin_width = (max_v - min_v) / bin_count
        bins = [min_v + i * bin_width for i in range(bin_count + 1)]
        counts = [0] * bin_count
        idx = 0
        for v in values:
            while idx < bin_count and v > bins[idx + 1]:
                idx += 1
            if idx < bin_count:
                counts[idx] += 1

    bin_labels = [f"{bins[i]:.1f}-{bins[i+1]:.1f}" for i in range(bin_count)]

    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": bin_labels,
            "axisLabel": {"rotate": 45},
        },
        "yAxis": {"type": "value"},
        "series": [{
            "type": "bar",
            "data": counts,
            "barWidth": "90%",
        }],
        "grid": {"left": 60, "right": 30, "bottom": 80},
    }


# ── Public API ──────────────────────────────────────────


_BUILDERS = {
    "line": _build_line_option,
    "bar": _build_bar_option,
    "pie": _build_pie_option,
    "scatter": _build_scatter_option,
    "histogram": _build_histogram_option,
}


class ChartTool:
    """Rule-based chart generator — no LLM, no DB access, no schema reads."""

    def render(
        self,
        result: QueryResult,
        task_plan: Optional[TaskPlan] = None,
    ) -> ChartResult:
        """Analyse a QueryResult and return a ChartResult with ECharts option."""
        if not result.columns or not result.rows:
            return ChartResult(supported=False)

        # Build column metadata from result
        columns = [{"column_name": c} for c in result.columns]
        rows = result.rows

        chart_type = detect_chart_type(columns, rows, task_plan)

        if chart_type == "none":
            return ChartResult(supported=False)

        col_classes = _classify_columns(columns)
        builder = _BUILDERS.get(chart_type)
        if builder is None:
            return ChartResult(supported=False)

        option = builder(columns, rows, col_classes)

        x_field, y_field = None, None
        if col_classes["time"] or col_classes["category"]:
            x_field = (col_classes["time"] or col_classes["category"])[0]
        if col_classes["numeric"]:
            y_field = col_classes["numeric"][0]

        return ChartResult(
            chart_type=chart_type,
            echarts_option=option,
            title=task_plan.task_type if task_plan else None,
            x_field=x_field,
            y_field=y_field,
            supported=True,
        )
