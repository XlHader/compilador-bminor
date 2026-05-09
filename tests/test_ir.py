from __future__ import annotations

# pyright: reportMissingImports=false
from pathlib import Path

from proyect.ir import (
    IRDiagnostic,
    IRInstruction,
    IRResult,
    LabelGenerator,
    RegisterGenerator,
    format_ir,
    generate_ir,
    type_suffix,
)
from proyect.parser import parse_bminor
from proyect.semantic import PrimitiveType, analyze_semantic


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


def _ops(source: str) -> list[tuple[object, ...]]:
    return _ir(source).to_tuples()


def test_ir_instruction_exposes_tuple_form() -> None:
    instruction = IRInstruction("ADDI", ("R1", "R2", "R3"))

    assert instruction.as_tuple() == ("ADDI", "R1", "R2", "R3")
    assert tuple(instruction) == ("ADDI", "R1", "R2", "R3")


def test_ir_result_reports_success_and_formats_instructions() -> None:
    result = IRResult(
        instructions=[
            IRInstruction("MOVI", (2, "R1")),
            IRInstruction("STOREI", ("R1", "a")),
        ]
    )

    assert result.ok
    assert result.to_tuples() == [
        ("MOVI", 2, "R1"),
        ("STOREI", "R1", "a"),
    ]
    assert format_ir(result) == "MOVI 2, R1\nSTOREI R1, a"


def test_ir_result_reports_diagnostics() -> None:
    result = IRResult(diagnostics=[IRDiagnostic("boom", 1, 2)])

    assert not result.ok
    assert result.to_tuples() == []


def test_register_and_label_generation_is_deterministic() -> None:
    registers = RegisterGenerator()
    labels = LabelGenerator()

    assert [registers.new() for _ in range(3)] == ["R1", "R2", "R3"]
    assert [labels.new("if") for _ in range(2)] == ["if1", "if2"]


def test_type_suffix_maps_semantic_types_to_ir_families() -> None:
    assert type_suffix(PrimitiveType("integer")) == "I"
    assert type_suffix(PrimitiveType("boolean")) == "I"
    assert type_suffix(PrimitiveType("float")) == "F"
    assert type_suffix(PrimitiveType("char")) == "B"
    assert type_suffix(PrimitiveType("string")) == "S"


def test_generate_ir_rejects_semantic_errors() -> None:
    parsed = parse_bminor("main: function void () = { missing = 1; }")
    assert parsed.ast is not None
    semantic = analyze_semantic(parsed.ast)
    assert semantic.errors

    result = generate_ir(parsed.ast, semantic)

    assert not result.ok
    assert result.instructions == []
    assert "semantically valid" in result.diagnostics[0].message


def test_generate_ir_lowers_empty_void_main() -> None:
    tuples = _ops("main: function void () = { }")

    assert tuples == [("LABEL", "main"), ("RET",)]


def test_generate_ir_does_not_add_duplicate_return() -> None:
    tuples = _ops("main: function integer () = { return 0; }")

    assert tuples == [("LABEL", "main"), ("MOVI", 0, "R1"), ("RET", "R1")]


def test_generate_ir_lowers_primitives_and_assignments() -> None:
    tuples = _ops(
        """
        a: integer = 2 + 3 * 4;
        flag: boolean = true;
        text: string = "ok";
        main: function integer () = {
            a += 5;
            print a, flag, text;
            return a;
        }
        """
    )

    assert ("VARI", "a") in tuples
    assert ("MULI", "R2", "R3", "R4") in tuples
    assert ("ADDI", "R1", "R4", "R5") in tuples
    assert ("VARS", "text") in tuples
    assert any(op[0] == "PRINTI" for op in tuples)
    assert any(op[0] == "PRINTS" for op in tuples)
    assert tuples[-1][0] == "RET"


def test_generate_ir_lowers_control_flow_and_ternary() -> None:
    tuples = _ops(
        """
        main: function integer () = {
            i: integer = 0;
            while (i < 3) {
                if (i == 1) {
                    print i == 1 ? i : 0;
                } else {
                    print 0;
                }
                i++;
            }
            return i;
        }
        """
    )

    assert any(op[0] == "CBRANCH" for op in tuples)
    assert any(op[0] == "BRANCH" for op in tuples)
    assert any(op[0] == "PHI" for op in tuples)


def test_generate_ir_emits_fallthrough_return_for_partial_returns() -> None:
    tuples = _ops(
        """
        main: function integer () = {
            if (false) {
                return 1;
            }
        }
        """
    )

    assert tuples[-2][0] == "MOVI"
    assert tuples[-2][1] == 0
    assert tuples[-1] == ("RET", tuples[-2][-1])


def test_generate_ir_uses_distinct_storage_for_shadowed_locals() -> None:
    tuples = _ops(
        """
        main: function void () = {
            x: integer = 1;
            {
                x: integer = 2;
                print x;
            }
            print x;
        }
        """
    )

    allocs = [
        instruction for instruction in tuples if instruction[0] == "ALLOCI"
    ]
    assert len(allocs) == 2
    assert allocs[0][1] == "x"
    assert allocs[1][1] != "x"


def test_generate_ir_lowers_power_operator_as_exponentiation() -> None:
    tuples = _ops("main: function integer () = { return 2 ^ 3; }")

    assert any(instruction[0] == "POWI" for instruction in tuples)
    assert not any(instruction[0] == "XOR" for instruction in tuples)


def test_generate_ir_lowers_functions_and_calls() -> None:
    tuples = _ops(
        """
        add: function integer (a: integer, b: integer) = {
            return a + b;
        }
        main: function integer () = {
            return add(1, 2);
        }
        """
    )

    assert ("LABEL", "add") in tuples
    assert ("PARAMI", "a") in tuples
    assert ("PARAMI", "b") in tuples
    assert any(op[0] == "CALL" and op[1] == "add" for op in tuples)


def test_generate_ir_lowers_arrays_and_indexing() -> None:
    tuples = _ops(
        """
        values: array [3] integer = {1, 2, 3};
        main: function integer () = {
            values[1] = array_length(values);
            return values[1];
        }
        """
    )

    assert ("VARREF", "values") in tuples
    assert any(op[0] == "NEWARRAY" for op in tuples)
    assert any(op[0] == "ASTORE" for op in tuples)
    assert any(op[0] == "ALOAD" for op in tuples)
    assert any(op[0] == "ALENGTH" for op in tuples)


def test_generate_ir_lowers_objects_members_and_methods() -> None:
    tuples = _ops(
        """
        Box: class = {
            value: integer;
            init: function void (n: integer) = { value = n; }
            get: function integer () = { return value; }
        }
        main: function integer () = {
            b: Box;
            b = new Box(7);
            b.value = b.get();
            return b.value;
        }
        """
    )

    assert ("LABEL", "Box.init") in tuples
    assert ("LABEL", "Box.get") in tuples
    assert any(op[0] == "NEWOBJ" and op[1] == "Box" for op in tuples)
    assert any(op[0] == "CALL" and op[1] == "Box.init" for op in tuples)
    assert any(op[0] == "CALL" and op[1] == "Box.get" for op in tuples)
    assert any(op[0] == "GETFIELD" for op in tuples)
    assert any(op[0] == "SETFIELD" for op in tuples)


def test_generate_ir_lowers_unqualified_method_calls_with_self() -> None:
    tuples = _ops(
        """
        Box: class = {
            value: integer;
            get: function integer () = { return value; }
            twice: function integer () = { return get() + get(); }
        }
        main: function integer () = {
            b: Box;
            b = new Box();
            return b.twice();
        }
        """
    )

    calls = [instruction for instruction in tuples if instruction[0] == "CALL"]
    assert ("CALL", "get", "R1") not in calls
    assert any(
        instruction[1] == "Box.get" and instruction[2] == "self"
        for instruction in calls
    )


def test_cli_prints_ir_output(capsys) -> None:
    from proyect.main import main

    path = Path("examples/parser.bp")
    assert path.exists()

    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["proyect.main", str(path), "--ir", "--no-tree"]
        assert main() == 0
        output = capsys.readouterr().out
        assert "IR Code" in output
        assert "LABEL main" in output
    finally:
        sys.argv = original_argv
