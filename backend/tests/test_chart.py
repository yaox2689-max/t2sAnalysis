"""Tests for Chart Tool — type detection, option builders, and edge cases."""

import pytest

from app.models.query import QueryResult
from app.models.task import TaskPlan
from app.tools.chart import (
    ChartTool,
    detect_chart_type,
)


@pytest.fixture
def tool():
    return ChartTool()


# ── detect_chart_type ────────────────────────────────────


class TestDetect:
    def test_empty_rows_returns_none(self):
        assert detect_chart_type([{"column_name": "a"}], []) == "none"

    def test_single_row_returns_none(self):
        assert detect_chart_type([{"column_name": "a"}], [{"a": 1}]) == "none"

    def test_time_and_number_is_line(self):
        cols = [{"column_name": "date"}, {"column_name": "sales"}]
        rows = [{"date": "2024-01", "sales": 100}, {"date": "2024-02", "sales": 200}]
        assert detect_chart_type(cols, rows) == "line"

    def test_category_and_number_is_bar(self):
        cols = [{"column_name": "category"}, {"column_name": "sales"}]
        rows = [{"category": f"Cat{i}", "sales": i * 10} for i in range(1, 15)]
        assert detect_chart_type(cols, rows) == "bar"

    def test_category_single_and_few_rows_is_pie(self):
        cols = [{"column_name": "category"}, {"column_name": "sales"}]
        rows = [{"category": "A", "sales": 10}, {"category": "B", "sales": 20},
                {"category": "C", "sales": 15}]
        assert detect_chart_type(cols, rows) == "pie"

    def test_two_numeric_is_scatter(self):
        cols = [{"column_name": "height"}, {"column_name": "weight"}]
        rows = [{"height": 170, "weight": 65}, {"height": 180, "weight": 80}]
        assert detect_chart_type(cols, rows) == "scatter"

    def test_single_numeric_is_histogram(self):
        cols = [{"column_name": "score"}]
        rows = [{"score": 50}, {"score": 60}, {"score": 70}]
        assert detect_chart_type(cols, rows) == "histogram"

    def test_hint_overrides_detection(self):
        """chart_type_hint is NOT used for category+num case (pie/bar chosen by rule)."""
        cols = [{"column_name": "category"}, {"column_name": "sales"}]
        rows = [{"category": "A", "sales": 10}, {"category": "B", "sales": 20}]
        plan = TaskPlan(task_type="query", chart_type_hint="line")
        # 2 rows, cat+num → pie, not line
        assert detect_chart_type(cols, rows, plan) == "pie"


# ── ChartTool.render ─────────────────────────────────────


class TestRender:
    def test_empty_result_unsupported(self, tool):
        result = QueryResult(columns=[], rows=[])
        out = tool.render(result)
        assert out.supported is False

    def test_line_chart(self, tool):
        result = QueryResult(
            columns=["month", "sales"],
            rows=[{"month": "Jan", "sales": 100}, {"month": "Feb", "sales": 200}],
        )
        plan = TaskPlan(task_type="trend")
        out = tool.render(result, plan)
        assert out.supported is True
        assert out.chart_type == "line"
        assert out.echarts_option.get("series") is not None

    def test_bar_chart(self, tool):
        result = QueryResult(
            columns=["category", "sales"],
            rows=[{"category": f"A{i}", "sales": i*10} for i in range(1, 10)],
        )
        out = tool.render(result)
        assert out.supported is True
        assert out.chart_type == "bar"

    def test_pie_chart(self, tool):
        result = QueryResult(
            columns=["category", "value"],
            rows=[{"category": "A", "value": 30}, {"category": "B", "value": 20},
                  {"category": "C", "value": 50}],
        )
        out = tool.render(result)
        assert out.supported is True
        assert out.chart_type == "pie"

    def test_scatter_chart(self, tool):
        result = QueryResult(
            columns=["height", "weight"],
            rows=[{"height": 170, "weight": 65}, {"height": 180, "weight": 80},
                  {"height": 160, "weight": 55}],
        )
        out = tool.render(result)
        assert out.supported is True
        assert out.chart_type == "scatter"

    def test_histogram_chart(self, tool):
        result = QueryResult(
            columns=["score"],
            rows=[{"score": 50}, {"score": 60}, {"score": 70}, {"score": 80}],
        )
        out = tool.render(result)
        assert out.supported is True
        assert out.chart_type == "histogram"

    def test_single_row_unsupported(self, tool):
        result = QueryResult(columns=["a"], rows=[{"a": 1}])
        out = tool.render(result)
        assert out.supported is False

    def test_chart_result_has_metadata(self, tool):
        result = QueryResult(columns=["month", "sales"],
                             rows=[{"month": "Jan", "sales": 100},
                                   {"month": "Feb", "sales": 200}])
        plan = TaskPlan(task_type="trend")
        out = tool.render(result, plan)
        assert out.title == "trend"
        assert out.x_field == "month"
        assert out.y_field == "sales"

    def test_hint_respected(self, tool):
        """When no rule matches, fallback to chart_type_hint."""
        result = QueryResult(columns=["a", "b"],
                             rows=[{"a": "x", "b": 1}, {"a": "y", "b": 2},
                                   {"a": "z", "b": 3}, {"a": "w", "b": 4},
                                   {"a": "v", "b": 5}, {"a": "u", "b": 6},
                                   {"a": "t", "b": 7}, {"a": "s", "b": 8},
                                   {"a": "r", "b": 9}, {"a": "q", "b": 10}])
        plan = TaskPlan(task_type="query", chart_type_hint="bar")
        out = tool.render(result, plan)
        # 10 cats + 1 num → bar, hint matches
        assert out.chart_type == "bar"
