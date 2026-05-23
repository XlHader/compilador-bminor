from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from .models import IRInstruction, IRResult

_BINARY_OPS = {
    "ADDI",
    "SUBI",
    "MULI",
    "DIVI",
    "MODI",
    "POWI",
    "ADDF",
    "SUBF",
    "MULF",
    "DIVF",
    "MODF",
    "POWF",
    "AND",
    "OR",
    "XOR",
    "CONCATS",
}
_COMPARE_OPS = {"CMPI", "CMPF", "CMPB", "CMPS"}
_MOV_OPS = {"MOVI", "MOVF", "MOVB", "MOVS"}
_PURE_FIXED_OPS = (
    _MOV_OPS
    | _BINARY_OPS
    | _COMPARE_OPS
    | {
        "ALOAD",
        "GETFIELD",
        "ALENGTH",
        "PHI",
    }
)
_BARRIER_PREFIXES = (
    "STORE",
    "PARAM",
    "VAR",
    "ALLOC",
)
_BARRIER_OPS = {
    "LABEL",
    "CALL",
    "ASTORE",
    "SETFIELD",
    "NEWARRAY",
    "NEWOBJ",
    "DATAS",
}


def optimize_ir(result: IRResult, level: int = 0) -> IRResult:
    return IROptimizer(level).optimize(result)


class IROptimizer:
    def __init__(self, level: int = 0) -> None:
        if level < 0 or level > 2:
            raise ValueError("optimization level must be between 0 and 2")
        self.level = level

    def optimize(self, result: IRResult) -> IRResult:
        if self.level == 0 or result.diagnostics:
            return IRResult(
                instructions=list(result.instructions),
                diagnostics=list(result.diagnostics),
            )

        instructions = list(result.instructions)
        instructions = self.constant_fold_and_simplify(instructions)
        instructions = self.remove_unreachable(instructions)
        instructions = self.remove_branch_to_next_label(instructions)
        if self.level >= 2:
            instructions = self.remove_unused_temp_definitions(instructions)
        return IRResult(
            instructions=instructions,
            diagnostics=list(result.diagnostics),
        )

    def constant_fold_and_simplify(
        self,
        instructions: list[IRInstruction],
    ) -> list[IRInstruction]:
        constants: dict[str, Any] = {}
        out: list[IRInstruction] = []

        for instruction in instructions:
            op = instruction.op
            args = instruction.args

            if op == "LABEL":
                constants.clear()
                out.append(instruction)
                continue

            replacement = self._fold_instruction(instruction, constants)
            out.append(replacement)

            dst = self.defined_temp(replacement)
            if dst is not None:
                value = self._constant_defined_by(replacement)
                if value is None:
                    constants.pop(dst, None)
                else:
                    constants[dst] = value

            if self._is_barrier(op, args):
                constants.clear()

        return out

    def remove_unreachable(
        self,
        instructions: list[IRInstruction],
    ) -> list[IRInstruction]:
        out: list[IRInstruction] = []
        unreachable = False
        for instruction in instructions:
            if instruction.op == "LABEL":
                unreachable = False
                out.append(instruction)
                continue
            if unreachable:
                continue
            out.append(instruction)
            if instruction.op in {"BRANCH", "RET"}:
                unreachable = True
        return out

    def remove_branch_to_next_label(
        self,
        instructions: list[IRInstruction],
    ) -> list[IRInstruction]:
        out: list[IRInstruction] = []
        index = 0
        while index < len(instructions):
            instruction = instructions[index]
            if (
                instruction.op == "BRANCH"
                and len(instruction.args) == 1
                and index + 1 < len(instructions)
            ):
                next_instruction = instructions[index + 1]
                if (
                    next_instruction.op == "LABEL"
                    and next_instruction.args == instruction.args
                ):
                    index += 1
                    continue
            out.append(instruction)
            index += 1
        return out

    def remove_unused_temp_definitions(
        self,
        instructions: list[IRInstruction],
    ) -> list[IRInstruction]:
        used: set[str] = set()
        result_reversed: list[IRInstruction] = []

        for instruction in reversed(instructions):
            dst = self.defined_temp(instruction)
            args = self.used_temps(instruction)
            if (
                dst is not None
                and dst not in used
                and self.is_pure_definition(instruction)
            ):
                continue
            if dst is not None:
                used.discard(dst)
            used.update(args)
            result_reversed.append(instruction)

        return list(reversed(result_reversed))

    def defined_temp(self, instruction: IRInstruction) -> str | None:
        op = instruction.op
        args = instruction.args
        candidate: object | None = None
        if op in _MOV_OPS and len(args) == 2:
            candidate = args[1]
        elif op in _BINARY_OPS and len(args) == 3:
            candidate = args[2]
        elif op in _COMPARE_OPS and len(args) == 4:
            candidate = args[3]
        elif op.startswith("LOAD") and len(args) == 2:
            candidate = args[1]
        elif op in {"ALOAD", "GETFIELD"} and len(args) == 3:
            candidate = args[2]
        elif op == "ALENGTH" and len(args) == 2:
            candidate = args[1]
        elif op == "PHI" and len(args) == 2:
            candidate = args[1]
        elif op == "CALL" and len(args) >= 2:
            candidate = args[-1]
        elif op in {"NEWOBJ", "NEWARRAY"} and len(args) >= 2:
            candidate = args[-1]
        if isinstance(candidate, str) and self._is_temp(candidate):
            return candidate
        return None

    def used_temps(self, instruction: IRInstruction) -> set[str]:
        op = instruction.op
        args = instruction.args
        if op in _MOV_OPS or op == "LABEL":
            return set()
        if op == "BRANCH":
            return set()
        if op == "CBRANCH":
            return self._temps_in(args[:1])
        if op in _BINARY_OPS:
            return self._temps_in(args[:2])
        if op in _COMPARE_OPS:
            return self._temps_in(args[1:3])
        if op.startswith("STORE"):
            return self._temps_in(args[:1])
        if op.startswith("PRINT") or op == "RET":
            return self._temps_in(args)
        if op.startswith("LOAD"):
            return self._temps_in(args[:1])
        if op == "ALOAD":
            return self._temps_in(args[:2])
        if op == "GETFIELD":
            return self._temps_in(args[:1])
        if op == "SETFIELD":
            return self._temps_in(args[:2])
        if op == "ASTORE":
            return self._temps_in(args)
        if op == "ALENGTH":
            return self._temps_in(args[:1])
        if op == "PHI":
            return self._temps_in(self._flatten(args[:1]))
        if op == "CALL":
            return self._temps_in(args[1:-1])
        if op == "NEWARRAY":
            return self._temps_in(args[1:-1])
        if op == "NEWOBJ":
            return set()
        if op.startswith(("PARAM", "VAR", "ALLOC")):
            return set()
        return self._temps_in(args)

    def is_pure_definition(self, instruction: IRInstruction) -> bool:
        return instruction.op in _PURE_FIXED_OPS or instruction.op.startswith(
            "LOAD"
        )

    def _fold_instruction(
        self,
        instruction: IRInstruction,
        constants: dict[str, Any],
    ) -> IRInstruction:
        op = instruction.op
        args = instruction.args
        if op in _BINARY_OPS and len(args) == 3:
            return self._fold_binary(instruction, constants)
        if op in _COMPARE_OPS and len(args) == 4:
            return self._fold_compare(instruction, constants)
        if op == "CBRANCH" and len(args) == 3:
            test = self._constant_value(args[0], constants)
            if test is not None:
                label = args[1] if bool(test) else args[2]
                return IRInstruction("BRANCH", (label,))
        return instruction

    def _fold_binary(
        self,
        instruction: IRInstruction,
        constants: dict[str, Any],
    ) -> IRInstruction:
        left, right, dst = instruction.args
        left_value = self._constant_value(left, constants)
        right_value = self._constant_value(right, constants)

        if left_value is not None and right_value is not None:
            folded = self._eval_binary(instruction.op, left_value, right_value)
            if folded is not None:
                return self._constant_instruction(instruction.op, folded, dst)

        simplified = self._simplify_binary(
            instruction.op,
            left,
            right,
            dst,
            left_value,
            right_value,
        )
        return simplified if simplified is not None else instruction

    def _fold_compare(
        self,
        instruction: IRInstruction,
        constants: dict[str, Any],
    ) -> IRInstruction:
        operator, left, right, dst = instruction.args
        left_value = self._constant_value(left, constants)
        right_value = self._constant_value(right, constants)
        if left_value is None or right_value is None:
            return instruction
        try:
            result = self._eval_compare(str(operator), left_value, right_value)
        except ValueError:
            return instruction
        return IRInstruction("MOVI", (1 if result else 0, dst))

    def _simplify_binary(
        self,
        op: str,
        left: object,
        right: object,
        dst: object,
        left_value: Any,
        right_value: Any,
    ) -> IRInstruction | None:
        if op == "MULI":
            if left_value == 0 or right_value == 0:
                return self._constant_instruction(op, 0, dst)
            if left_value == 1 and right_value is not None:
                return self._constant_instruction(op, right_value, dst)
            if right_value == 1 and left_value is not None:
                return self._constant_instruction(op, left_value, dst)
        if op == "MULF":
            if left_value == 1 and right_value is not None:
                return self._constant_instruction(op, right_value, dst)
            if right_value == 1 and left_value is not None:
                return self._constant_instruction(op, left_value, dst)
        if op in {"ADDI", "ADDF"}:
            if left_value == 0 and right_value is not None:
                return self._constant_instruction(op, right_value, dst)
            if right_value == 0 and left_value is not None:
                return self._constant_instruction(op, left_value, dst)
        if op in {"SUBI", "SUBF"} and right_value == 0:
            if left_value is not None:
                return self._constant_instruction(op, left_value, dst)
        if op in {"DIVI", "DIVF"} and right_value == 1:
            if left_value is not None:
                return self._constant_instruction(op, left_value, dst)
        if op == "AND" and (left_value == 0 or right_value == 0):
            return IRInstruction("MOVI", (0, dst))
        if op == "OR" and (left_value == 1 or right_value == 1):
            return IRInstruction("MOVI", (1, dst))
        return None

    def _constant_defined_by(self, instruction: IRInstruction) -> Any:
        if instruction.op in _MOV_OPS and len(instruction.args) == 2:
            return instruction.args[0]
        return None

    def _constant_value(
        self,
        value: object,
        constants: dict[str, Any],
    ) -> Any:
        if isinstance(value, str) and self._is_temp(value):
            return constants.get(value)
        if isinstance(value, int | float | str | bool):
            return value
        return None

    def _eval_binary(self, op: str, left: Any, right: Any) -> Any:
        if op in {"DIVI", "DIVF", "MODI", "MODF"} and right == 0:
            return None
        if op.startswith("ADD"):
            return left + right
        if op.startswith("SUB"):
            return left - right
        if op.startswith("MUL"):
            return left * right
        if op == "DIVI":
            return self._c_div(int(left), int(right))
        if op == "DIVF":
            return left / right
        if op == "MODI":
            return self._c_mod(int(left), int(right))
        if op == "MODF":
            return math.fmod(left, right)
        if op.startswith("POW"):
            return left**right
        if op == "AND":
            return 1 if bool(left) and bool(right) else 0
        if op == "OR":
            return 1 if bool(left) or bool(right) else 0
        if op == "XOR":
            return 1 if bool(left) ^ bool(right) else 0
        if op == "CONCATS":
            return str(left) + str(right)
        return None

    def _c_div(self, left: int, right: int) -> int:
        quotient = abs(left) // abs(right)
        if (left < 0) != (right < 0):
            return -quotient
        return quotient

    def _c_mod(self, left: int, right: int) -> int:
        return left - self._c_div(left, right) * right

    def _eval_compare(self, operator: str, left: Any, right: Any) -> bool:
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator == "<":
            return left < right
        if operator == "<=":
            return left <= right
        if operator == ">":
            return left > right
        if operator == ">=":
            return left >= right
        raise ValueError(f"unsupported comparator: {operator}")

    def _constant_instruction(
        self,
        source_op: str,
        value: Any,
        dst: object,
    ) -> IRInstruction:
        if source_op.endswith("F"):
            return IRInstruction("MOVF", (value, dst))
        if source_op == "CONCATS":
            return IRInstruction("MOVS", (value, dst))
        return IRInstruction("MOVI", (value, dst))

    def _is_barrier(self, op: str, args: tuple[object, ...]) -> bool:
        return (
            op in _BARRIER_OPS
            or op.startswith(_BARRIER_PREFIXES)
            or op.startswith("STORE")
            or op.startswith("PRINT")
            or op == "RET"
            or (op == "CALL" and len(args) > 0)
        )

    def _temps_in(self, values: Iterable[object]) -> set[str]:
        return {
            value
            for value in values
            if isinstance(value, str) and self._is_temp(value)
        }

    def _flatten(self, values: Iterable[object]) -> list[object]:
        flattened: list[object] = []
        for value in values:
            if isinstance(value, tuple):
                flattened.extend(self._flatten(value))
            else:
                flattened.append(value)
        return flattened

    def _is_temp(self, value: object) -> bool:
        return isinstance(value, str) and value.startswith("R")


__all__ = ["IROptimizer", "optimize_ir"]
