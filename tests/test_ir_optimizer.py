from __future__ import annotations

# pyright: reportMissingImports=false
import os
import subprocess
from pathlib import Path

import pytest

from proyect.ir import IRInstruction, IRResult, optimize_ir

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"


def _result(*tuples: tuple[object, ...]) -> IRResult:
    return IRResult(
        instructions=[
            IRInstruction(str(instruction[0]), tuple(instruction[1:]))
            for instruction in tuples
        ]
    )


def _optimize(
    tuples: list[tuple[object, ...]],
    level: int,
) -> list[tuple[object, ...]]:
    return optimize_ir(_result(*tuples), level=level).to_tuples()


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PYTHON), "-m", "proyect.main", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )


def test_optimize_ir_o0_preserves_ir_result() -> None:
    result = _result(("MOVI", 2, "R1"), ("PRINTI", "R1"))

    optimized = optimize_ir(result, level=0)

    assert optimized.to_tuples() == result.to_tuples()
    assert optimized.diagnostics == result.diagnostics


def test_o1_folds_constants_and_supported_project_operations() -> None:
    tuples = [
        ("MOVI", 2, "R1"),
        ("MOVI", 3, "R2"),
        ("ADDI", "R1", "R2", "R3"),
        ("MOVF", 2.0, "R4"),
        ("MOVF", 4.0, "R5"),
        ("DIVF", "R5", "R4", "R6"),
        ("MOVS", "a", "R7"),
        ("MOVS", "b", "R8"),
        ("CONCATS", "R7", "R8", "R9"),
        ("PRINTI", "R3"),
    ]

    out = _optimize(tuples, level=1)

    assert ("MOVI", 5, "R3") in out
    assert ("MOVF", 2.0, "R6") in out
    assert ("MOVS", "ab", "R9") in out


def test_o1_preserves_division_and_modulo_by_zero() -> None:
    tuples = [
        ("MOVI", 4, "R1"),
        ("MOVI", 0, "R2"),
        ("DIVI", "R1", "R2", "R3"),
        ("MODI", "R1", "R2", "R4"),
    ]

    out = _optimize(tuples, level=1)

    assert ("DIVI", "R1", "R2", "R3") in out
    assert ("MODI", "R1", "R2", "R4") in out


def test_o1_folds_integer_division_and_modulo_with_c_semantics() -> None:
    tuples = [
        ("MOVI", -3, "R1"),
        ("MOVI", 2, "R2"),
        ("DIVI", "R1", "R2", "R3"),
        ("MODI", "R1", "R2", "R4"),
        ("MOVI", 3, "R5"),
        ("MOVI", -2, "R6"),
        ("DIVI", "R5", "R6", "R7"),
        ("MODI", "R5", "R6", "R8"),
    ]

    out = _optimize(tuples, level=1)

    assert ("MOVI", -1, "R3") in out
    assert ("MOVI", -1, "R4") in out
    assert ("MOVI", -1, "R7") in out
    assert ("MOVI", 1, "R8") in out


def test_o1_simplifies_safe_algebraic_identities() -> None:
    tuples = [
        ("LOADI", "x", "R1"),
        ("MOVI", 0, "R2"),
        ("MULI", "R1", "R2", "R3"),
        ("MOVI", 10, "R4"),
        ("MOVI", 1, "R5"),
        ("MULI", "R4", "R5", "R6"),
        ("PRINTI", "R3"),
        ("PRINTI", "R6"),
    ]

    out = _optimize(tuples, level=1)

    assert ("MOVI", 0, "R3") in out
    assert ("MOVI", 10, "R6") in out


def test_o1_does_not_simplify_unknown_float_multiply_by_zero() -> None:
    tuples = [
        ("LOADF", "x", "R1"),
        ("MOVF", 0.0, "R2"),
        ("MULF", "R1", "R2", "R3"),
        ("PRINTF", "R3"),
    ]

    out = _optimize(tuples, level=1)

    assert ("MULF", "R1", "R2", "R3") in out
    assert ("MOVF", 0.0, "R3") not in out


def test_o1_simplifies_constant_comparisons_and_branches() -> None:
    tuples = [
        ("MOVI", 1, "R1"),
        ("MOVI", 2, "R2"),
        ("CMPI", "<", "R1", "R2", "R3"),
        ("CBRANCH", "R3", "Ltrue", "Lfalse"),
        ("LABEL", "Ltrue"),
        ("PRINTI", "R1"),
        ("BRANCH", "Lend"),
        ("MOVI", 99, "R9"),
        ("LABEL", "Lfalse"),
        ("BRANCH", "Lend"),
        ("LABEL", "Lend"),
        ("RET", "R1"),
    ]

    out = _optimize(tuples, level=1)

    assert ("MOVI", 1, "R3") in out
    assert ("LABEL", "Ltrue") in out
    assert ("CBRANCH", "R3", "Ltrue", "Lfalse") not in out
    assert ("MOVI", 99, "R9") not in out
    assert out.count(("BRANCH", "Lend")) == 1


def test_o2_removes_unused_pure_temporary_definitions() -> None:
    tuples = [
        ("MOVI", 2, "R1"),
        ("MOVI", 99, "R2"),
        ("ADDI", "R1", "R1", "R3"),
        ("PRINTI", "R3"),
    ]

    out = _optimize(tuples, level=2)

    assert ("MOVI", 99, "R2") not in out
    assert ("MOVI", 4, "R3") in out
    assert ("PRINTI", "R3") in out


def test_o2_preserves_side_effecting_structural_and_unknown_instructions() -> (
    None
):
    tuples = [
        ("MOVI", 1, "R1"),
        ("STOREI", "R1", "x"),
        ("PRINTI", "R1"),
        ("CALL", "work", "R1", "R2"),
        ("NEWOBJ", "Box", "R3"),
        ("ASTORE", "R1", "R3", "R1"),
        ("MYSTERY", "R1", "R4"),
    ]

    out = _optimize(tuples, level=2)

    assert ("STOREI", "R1", "x") in out
    assert ("PRINTI", "R1") in out
    assert ("CALL", "work", "R1", "R2") in out
    assert ("NEWOBJ", "Box", "R3") in out
    assert ("ASTORE", "R1", "R3", "R1") in out
    assert ("MYSTERY", "R1", "R4") in out


def test_o1_does_not_carry_constants_across_barriers() -> None:
    tuples = [
        ("MOVI", 2, "R1"),
        ("LABEL", "L1"),
        ("MOVI", 3, "R2"),
        ("ADDI", "R1", "R2", "R3"),
        ("CALL", "touch", "_"),
        ("MOVI", 4, "R4"),
        ("ADDI", "R2", "R4", "R5"),
    ]

    out = _optimize(tuples, level=1)

    assert ("ADDI", "R1", "R2", "R3") in out
    assert ("ADDI", "R2", "R4", "R5") in out


def test_cli_ir_without_optimization_matches_o0() -> None:
    plain = _run_cli("examples/opt1.bminor", "--ir", "--no-tree")
    optimized = _run_cli(
        "examples/opt1.bminor",
        "--ir",
        "--no-tree",
        "-O0",
    )

    assert plain.returncode == 0
    assert optimized.returncode == 0
    assert plain.stdout == optimized.stdout


def test_cli_o1_and_o2_apply_expected_safe_optimizations() -> None:
    o1 = _run_cli("examples/opt1.bminor", "--ir", "--no-tree", "-O1")
    o2 = _run_cli("examples/opt1.bminor", "--ir", "--no-tree", "-O2")

    assert o1.returncode == 0
    assert o2.returncode == 0
    assert "MOVI 14" in o1.stdout
    assert "MOVI 14" in o2.stdout


def test_cli_rejects_invalid_optimization_levels() -> None:
    result = _run_cli("examples/opt1.bminor", "--ir", "--no-tree", "-O9")

    assert result.returncode != 0
    assert (
        "optimization" in result.stderr.lower()
        or "optimización" in result.stderr.lower()
    )


@pytest.mark.parametrize(
    "example",
    [
        "examples/opt1.bminor",
        "examples/opt2.bminor",
        "examples/opt3.bminor",
        "examples/opt4.bminor",
    ],
)
def test_professor_examples_emit_ir_at_all_levels(example: str) -> None:
    for level in ["-O0", "-O1", "-O2"]:
        result = _run_cli(example, "--ir", "--no-tree", level)

        assert result.returncode == 0, result.stderr
        assert "IR Code" in result.stdout
