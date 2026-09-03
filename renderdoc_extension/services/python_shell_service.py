"""
Interactive Python shell support for the RenderDoc MCP bridge.
"""

import ast
import contextlib
import io
import json
import os
import time
import traceback


class PythonShellService:
    """Execute Python snippets against the live RenderDoc extension process."""

    def __init__(self, ctx, invoke, facade):
        self.ctx = ctx
        self._invoke = invoke
        self._facade = facade
        self._globals = {"__builtins__": __builtins__}
        self._refresh_bindings()

    def run_python_shell(self, code, run_on_replay_thread=False):
        """Execute Python code and return captured output plus the final expression value."""
        if not code or not code.strip():
            raise ValueError("code is required")

        self._refresh_bindings()

        stdout = io.StringIO()
        stderr = io.StringIO()
        started_at = time.time()

        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = self._run_code(code, run_on_replay_thread)
        except Exception:
            return {
                "ok": False,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "error": traceback.format_exc(),
                "duration_ms": int((time.time() - started_at) * 1000),
            }

        return {
            "ok": True,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
            "result": self._serialize_value(result),
            "result_type": type(result).__name__ if result is not None else "NoneType",
            "duration_ms": int((time.time() - started_at) * 1000),
        }

    def run_python_script(self, script_path, script_args=None, run_on_replay_thread=False):
        """Execute a Python script file inside the RenderDoc extension process."""
        if not script_path:
            raise ValueError("script_path is required")
        if not os.path.isfile(script_path):
            raise ValueError("script_path does not exist: %s" % script_path)

        script_args = [str(arg) for arg in (script_args or [])]
        self._refresh_bindings()

        stdout = io.StringIO()
        stderr = io.StringIO()
        started_at = time.time()

        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = self._run_script(script_path, script_args, run_on_replay_thread)
        except Exception:
            return {
                "ok": False,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "error": traceback.format_exc(),
                "duration_ms": int((time.time() - started_at) * 1000),
            }

        return {
            "ok": True,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
            "result": self._serialize_value(result),
            "result_type": type(result).__name__ if result is not None else "NoneType",
            "script_path": script_path,
            "script_args": script_args,
            "duration_ms": int((time.time() - started_at) * 1000),
        }

    def _refresh_bindings(self):
        """Keep helper bindings fresh across capture reloads."""
        self._globals["ctx"] = self.ctx
        self._globals["facade"] = self._facade
        self._globals["invoke"] = self._invoke

        try:
            import renderdoc as rd

            self._globals["rd"] = rd
        except ImportError:
            pass

        try:
            import qrenderdoc as qrd

            self._globals["qrd"] = qrd
        except ImportError:
            pass

    def _run_code(self, code, run_on_replay_thread):
        runner = lambda: self._execute_with_last_expr(code)
        if not run_on_replay_thread:
            return runner()

        box = {}

        def callback():
            box["result"] = runner()

        self._invoke(callback)
        return box.get("result")

    def _run_script(self, script_path, script_args, run_on_replay_thread):
        runner = lambda: self._execute_script_file(script_path, script_args)
        if not run_on_replay_thread:
            return runner()

        box = {}

        def callback():
            box["result"] = runner()

        self._invoke(callback)
        return box.get("result")

    def _execute_with_last_expr(self, code):
        tree = ast.parse(code, filename="<renderdoc-mcp-shell>", mode="exec")

        expression = None
        statements = tree.body
        if statements and isinstance(statements[-1], ast.Expr):
            expression = ast.Expression(statements[-1].value)
            ast.fix_missing_locations(expression)
            statements = statements[:-1]

        module = ast.Module(body=statements, type_ignores=[])
        ast.fix_missing_locations(module)

        exec(compile(module, "<renderdoc-mcp-shell>", "exec"), self._globals, self._globals)

        if expression is None:
            return None

        return eval(
            compile(expression, "<renderdoc-mcp-shell>", "eval"),
            self._globals,
            self._globals,
        )

    def _serialize_value(self, value):
        """Prefer raw JSON-compatible values and fall back to repr for RenderDoc objects."""
        try:
            json.dumps(value)
            return value
        except TypeError:
            return repr(value)

    def _execute_script_file(self, script_path, script_args):
        with open(script_path, "r", encoding="utf-8") as f:
            source = f.read()

        script_globals = dict(self._globals)
        script_globals.update(
            {
                "__file__": script_path,
                "__name__": "__main__",
                "__package__": None,
                "__cached__": None,
                "script_args": list(script_args),
            }
        )

        old_cwd = os.getcwd()
        script_dir = os.path.dirname(script_path) or old_cwd

        try:
            os.chdir(script_dir)
            exec(compile(source, script_path, "exec"), script_globals, script_globals)
        finally:
            os.chdir(old_cwd)

        if "__mcp_result__" in script_globals:
            return script_globals["__mcp_result__"]
        if "result" in script_globals:
            return script_globals["result"]
        return None
