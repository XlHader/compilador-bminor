from __future__ import annotations

# pyright: reportMissingImports=false
from pathlib import Path

from proyect.ir import IRInterpreter, IRResult, generate_ir
from proyect.parser import parse_bminor
from proyect.semantic import analyze_semantic


def _ir(source: str) -> IRResult:
    parsed = parse_bminor(source)
    assert parsed.ast is not None
    assert not parsed.lex_errors
    assert not parsed.parse_errors
    semantic = analyze_semantic(parsed.ast)
    assert not semantic.errors
    result = generate_ir(parsed.ast, semantic)
    assert result.ok, result.diagnostics
    return result


def _run(source: str) -> IRInterpreter:
    interpreter = IRInterpreter(_ir(source))
    interpreter.run("main")
    return interpreter


def test_interpreter_runs_generated_arithmetic_and_print_ir() -> None:
    interpreter = _run(
        """
        main: function integer () = {
            x: integer = 2 + 3 * 4;
            print x;
            return x;
        }
        """
    )

    assert interpreter.output == ["14"]
    assert interpreter.last_return == 14


def test_interpreter_runs_generated_control_flow_ir() -> None:
    interpreter = _run(
        """
        main: function integer () = {
            i: integer = 0;
            total: integer = 0;
            while (i < 4) {
                total += i;
                i++;
            }
            return total;
        }
        """
    )

    assert interpreter.last_return == 6


def test_interpreter_runs_generated_function_call_ir() -> None:
    interpreter = _run(
        """
        add: function integer (a: integer, b: integer) = {
            return a + b;
        }
        main: function integer () = {
            return add(5, 7);
        }
        """
    )

    assert interpreter.last_return == 12


def test_interpreter_runs_generated_arrays_ir() -> None:
    interpreter = _run(
        """
        values: array [3] integer = {1};
        main: function integer () = {
            values[1] = 9;
            return array_length(values) + values[1];
        }
        """
    )

    assert interpreter.last_return == 12


def test_interpreter_runs_generated_object_method_ir() -> None:
    interpreter = _run(
        """
        Box: class = {
            value: integer;
            init: function void (n: integer) = { value = n; }
            get: function integer () = { return value; }
        }
        main: function integer () = {
            b: Box;
            b = new Box(8);
            return b.get();
        }
        """
    )

    assert interpreter.last_return == 8


def test_cli_run_ir_executes_generated_ir(capsys) -> None:
    from proyect.main import main

    path = Path("examples/parser.bp")
    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["proyect.main", str(path), "--run-ir", "--no-tree"]
        assert main() == 0
        output = capsys.readouterr().out
        assert "IR Interpreter" in output
        assert "prints: ['parser ok']" in output
        assert "return: 0" in output
    finally:
        sys.argv = original_argv
