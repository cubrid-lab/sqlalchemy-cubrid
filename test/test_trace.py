# test/test_trace.py
"""Offline tests for the CUBRID trace utility module.

Tests verify import, API, and error handling without a live CUBRID connection.
Integration tests with a live DB are in test_integration.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sqlalchemy import text


class TestTraceImport:
    """Test trace module imports and exports."""

    def test_trace_query_importable_from_module(self):
        from sqlalchemy_cubrid.trace import trace_query

        assert callable(trace_query)

    def test_trace_query_importable_from_package(self):
        from sqlalchemy_cubrid import trace_query

        assert callable(trace_query)

    def test_trace_module_all(self):
        from sqlalchemy_cubrid.trace import __all__

        assert "trace_query" in __all__


class TestTraceQuery:
    """Test trace_query function behavior with mocked connections."""

    def test_trace_query_basic_flow(self):
        """trace_query should execute SET TRACE ON, statement, SHOW TRACE, SET TRACE OFF."""
        from sqlalchemy_cubrid.trace import trace_query

        conn = MagicMock()
        trace_result = MagicMock()
        trace_result.fetchall.return_value = [
            ("\nTrace Statistics:\n  SELECT (time: 0, fetch: 3)\n",)
        ]

        # execute calls: SET TRACE ON, the statement, SHOW TRACE, SET TRACE OFF
        call_count = [0]
        stmt_result = MagicMock()
        results = [None, stmt_result, trace_result, None]

        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return results[idx] if idx < len(results) else None

        conn.execute = MagicMock(side_effect=side_effect)

        stmt = text("SELECT * FROM users WHERE id = 1")
        output = trace_query(conn, stmt)

        assert len(output) == 1
        assert "Trace Statistics" in output[0]
        assert conn.execute.call_count == 4

    def test_trace_query_with_parameters(self):
        """trace_query should pass parameters to the statement execution."""
        from sqlalchemy_cubrid.trace import trace_query

        conn = MagicMock()
        trace_result = MagicMock()
        trace_result.fetchall.return_value = [("trace output",)]

        call_count = [0]
        stmt_result = MagicMock()
        results = [None, stmt_result, trace_result, None]

        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return results[idx] if idx < len(results) else None

        conn.execute = MagicMock(side_effect=side_effect)

        stmt = text("SELECT * FROM users WHERE id = :id")
        output = trace_query(conn, stmt, parameters={"id": 1})

        assert len(output) == 1
        # The second call (index 1) should include the parameters
        second_call = conn.execute.call_args_list[1]
        assert second_call[0][0] is stmt
        assert second_call[0][1] == {"id": 1}

    def test_trace_query_empty_result(self):
        """trace_query should return empty list when SHOW TRACE returns no rows."""
        from sqlalchemy_cubrid.trace import trace_query

        conn = MagicMock()
        trace_result = MagicMock()
        trace_result.fetchall.return_value = []

        call_count = [0]
        stmt_result = MagicMock()
        results = [None, stmt_result, trace_result, None]

        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return results[idx] if idx < len(results) else None

        conn.execute = MagicMock(side_effect=side_effect)

        stmt = text("SELECT 1")
        output = trace_query(conn, stmt)

        assert output == []

    def test_trace_query_null_trace_rows(self):
        """trace_query should skip None values in trace output."""
        from sqlalchemy_cubrid.trace import trace_query

        conn = MagicMock()
        trace_result = MagicMock()
        trace_result.fetchall.return_value = [(None,), ("actual trace",), (None,)]

        call_count = [0]
        stmt_result = MagicMock()
        results = [None, stmt_result, trace_result, None]

        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return results[idx] if idx < len(results) else None

        conn.execute = MagicMock(side_effect=side_effect)

        stmt = text("SELECT 1")
        output = trace_query(conn, stmt)

        assert len(output) == 1
        assert output[0] == "actual trace"

    def test_trace_query_always_disables_trace(self):
        """SET TRACE OFF should be called even if the statement raises an exception."""
        from sqlalchemy_cubrid.trace import trace_query

        conn = MagicMock()

        call_count = [0]

        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx == 1:  # The statement execution
                raise RuntimeError("query failed")
            return None

        conn.execute = MagicMock(side_effect=side_effect)

        stmt = text("SELECT * FROM nonexistent")
        with pytest.raises(RuntimeError, match="query failed"):
            trace_query(conn, stmt)

        # SET TRACE OFF should still be called (in finally block)
        # The last call should be a text() object containing SET TRACE OFF
        last_call = conn.execute.call_args_list[-1]
        last_arg = last_call[0][0]
        assert hasattr(last_arg, "text")
        assert last_arg.text == "SET TRACE OFF"

    def test_trace_query_multiple_trace_rows(self):
        """trace_query should handle multiple trace output rows."""
        from sqlalchemy_cubrid.trace import trace_query

        conn = MagicMock()
        trace_result = MagicMock()
        trace_result.fetchall.return_value = [
            ("Trace line 1",),
            ("Trace line 2",),
            ("Trace line 3",),
        ]

        call_count = [0]
        stmt_result = MagicMock()
        results = [None, stmt_result, trace_result, None]

        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return results[idx] if idx < len(results) else None

        conn.execute = MagicMock(side_effect=side_effect)

        stmt = text("SELECT 1")
        output = trace_query(conn, stmt)

        assert len(output) == 3
        assert output[0] == "Trace line 1"
        assert output[1] == "Trace line 2"
        assert output[2] == "Trace line 3"

    def test_trace_query_show_trace_read_failure_closes_both_results(self):
        """A SHOW TRACE read failure must release both handles and keep the original error."""

        from sqlalchemy_cubrid.trace import trace_query

        class TraceReadError(RuntimeError):
            pass

        conn = MagicMock()
        stmt_result = MagicMock()
        trace_result = MagicMock()
        trace_result.fetchall.side_effect = TraceReadError("SHOW TRACE read failed")

        call_count = [0]
        results = [None, stmt_result, trace_result]

        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx == 3:  # SET TRACE OFF during the cleanup block
                raise OSError("SET TRACE OFF failed")
            return results[idx] if idx < len(results) else None

        conn.execute = MagicMock(side_effect=side_effect)

        stmt = text("SELECT * FROM users")
        with pytest.raises(TraceReadError, match="SHOW TRACE read failed"):
            trace_query(conn, stmt)

        # The traced statement result and the SHOW TRACE result are both released,
        # even though reading the SHOW TRACE rows raised.
        stmt_result.close.assert_called_once_with()
        trace_result.close.assert_called_once_with()

        # SET TRACE OFF is still attempted, and its own failure is swallowed so the
        # TraceReadError above reaches the caller instead of being replaced.
        last_arg = conn.execute.call_args_list[-1][0][0]
        assert hasattr(last_arg, "text")
        assert last_arg.text == "SET TRACE OFF"
