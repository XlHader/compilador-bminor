from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import IRResult


class IRRuntimeError(RuntimeError):
    pass


@dataclass(slots=True)
class Frame:
    name: str
    instructions: list[tuple[object, ...]]
    locals: dict[str, Any] = field(default_factory=dict)
    regs: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, int] = field(default_factory=dict)
    pc: int = 0

    def __post_init__(self) -> None:
        self.labels = {
            str(inst[1]): idx
            for idx, inst in enumerate(self.instructions)
            if inst and inst[0] == "LABEL"
        }


@dataclass(frozen=True, slots=True)
class _Return:
    value: Any = None


class IRInterpreter:
    def __init__(self, program: IRResult | list[tuple], trace: bool = False):
        self.trace = trace
        self.instructions = _tuples(program)
        self.globals: dict[str, Any] = {}
        self.function_ranges: list[range] = []
        self.functions = self._split_functions(self.instructions)
        self.output: list[str] = []
        self.last_return: Any = None
        self._load_globals()

    def run(self, name: str = "main", *args: Any) -> Any:
        self.last_return = self.call(name, list(args))
        return self.last_return

    def call(self, name: str, args: list[Any]) -> Any:
        if name not in self.functions:
            raise IRRuntimeError(f"Función no encontrada: {name}")
        frame = Frame(name, list(self.functions[name]))
        param_insts = [inst for inst in frame.instructions if _is_param(inst)]
        if len(args) != len(param_insts):
            raise IRRuntimeError(
                f"La función {name} espera {len(param_insts)} argumento(s), "
                f"recibió {len(args)}"
            )
        for inst, value in zip(param_insts, args, strict=False):
            frame.locals[str(inst[1])] = value
        return self._execute_frame(frame)

    def _split_functions(
        self, instructions: list[tuple[object, ...]]
    ) -> dict[str, list[tuple[object, ...]]]:
        starts: list[tuple[str, int]] = []
        for idx, inst in enumerate(instructions):
            if (
                inst
                and inst[0] == "LABEL"
                and _is_function_label(str(inst[1]))
            ):
                starts.append((str(inst[1]), idx))
        functions: dict[str, list[tuple[object, ...]]] = {}
        for pos, (name, start) in enumerate(starts):
            next_start = (
                starts[pos + 1][1]
                if pos + 1 < len(starts)
                else len(instructions)
            )
            end = next_start
            for idx in range(start + 1, next_start):
                if instructions[idx][0] in _GLOBAL_OPS:
                    end = idx
                    break
            functions[name] = instructions[start:end]
            self.function_ranges.append(range(start, end))
        return functions

    def _load_globals(self) -> None:
        function_indexes = {
            idx for item_range in self.function_ranges for idx in item_range
        }
        frame = Frame(
            "<globals>",
            [
                inst
                for idx, inst in enumerate(self.instructions)
                if idx not in function_indexes
            ],
        )
        while frame.pc < len(frame.instructions):
            inst = frame.instructions[frame.pc]
            frame.pc += 1
            if inst[0] in _GLOBAL_OPS:
                self.globals.setdefault(
                    str(inst[1]), _default_for_op(str(inst[0]))
                )
            else:
                self._dispatch(frame, inst)

    def _execute_frame(self, frame: Frame) -> Any:
        while frame.pc < len(frame.instructions):
            pc = frame.pc
            inst = frame.instructions[frame.pc]
            frame.pc += 1
            if self.trace:
                print(f"[TRACE] {frame.name}:{pc:04d} {inst}")
            result = self._dispatch(frame, inst)
            if isinstance(result, _Return):
                return result.value
        return None

    def _dispatch(
        self, frame: Frame, inst: tuple[object, ...]
    ) -> _Return | None:
        op = str(inst[0])
        if op == "LABEL" or _is_param(inst):
            return None
        if op.startswith("ALLOC") or op.startswith("VAR"):
            frame.locals.setdefault(str(inst[1]), _default_for_op(op))
            return None
        if op.startswith("LOAD"):
            _, name, target = inst
            frame.regs[str(target)] = self._load_var(frame, str(name))
            return None
        if op.startswith("STORE"):
            _, source, name = inst
            self._store_var(frame, str(name), self._value(frame, source))
            return None
        if op.startswith("MOV"):
            _, value, target = inst
            frame.regs[str(target)] = _coerce_literal(op, value)
            return None
        if op in _ARITHMETIC:
            _, r1, r2, target = inst
            frame.regs[str(target)] = self._arithmetic(
                op, self._value(frame, r1), self._value(frame, r2)
            )
            return None
        if op in {"AND", "OR", "XOR"}:
            _, r1, r2, target = inst
            a = int(self._value(frame, r1))
            b = int(self._value(frame, r2))
            frame.regs[str(target)] = {
                "AND": a & b,
                "OR": a | b,
                "XOR": a ^ b,
            }[op]
            return None
        if op.startswith("CMP"):
            _, cmp_op, r1, r2, target = inst
            frame.regs[str(target)] = (
                1
                if _compare(
                    str(cmp_op), self._value(frame, r1), self._value(frame, r2)
                )
                else 0
            )
            return None
        if op == "CONCATS":
            _, r1, r2, target = inst
            frame.regs[str(target)] = str(self._value(frame, r1)) + str(
                self._value(frame, r2)
            )
            return None
        if op.startswith("PRINT"):
            value = self._value(frame, inst[1])
            text = (
                chr(value)
                if op == "PRINTB" and isinstance(value, int)
                else str(value)
            )
            self.output.append(text)
            return None
        if op == "BRANCH":
            frame.pc = frame.labels[str(inst[1])]
            return None
        if op == "CBRANCH":
            _, test, true_label, false_label = inst
            frame.pc = frame.labels[
                str(
                    true_label
                    if self._value(frame, test) != 0
                    else false_label
                )
            ]
            return None
        if op == "PHI":
            incoming = list(inst[1])
            target = str(inst[2])
            for _, reg in incoming:
                if reg in frame.regs:
                    frame.regs[target] = frame.regs[reg]
                    return None
            frame.regs[target] = self._value(frame, incoming[0][1])
            return None
        if op == "CALL":
            fname = str(inst[1])
            params = [p for p in self.functions.get(fname, []) if _is_param(p)]
            arg_values = [
                self._value(frame, arg) for arg in inst[2 : 2 + len(params)]
            ]
            target = (
                inst[2 + len(params)] if len(inst) > 2 + len(params) else None
            )
            ret = self.call(fname, arg_values)
            if target is not None and target != "_":
                frame.regs[str(target)] = ret
            return None
        if op == "RET":
            return _Return(
                None if len(inst) == 1 else self._value(frame, inst[1])
            )
        if op == "NEWARRAY":
            _, _element_type, length, target = inst
            frame.regs[str(target)] = [0] * int(self._value(frame, length))
            return None
        if op == "ALOAD":
            _, array, index, target = inst
            frame.regs[str(target)] = self._value(frame, array)[
                int(self._value(frame, index))
            ]
            return None
        if op == "ASTORE":
            _, source, array, index = inst
            self._value(frame, array)[int(self._value(frame, index))] = (
                self._value(frame, source)
            )
            return None
        if op == "ALENGTH":
            _, array, target = inst
            frame.regs[str(target)] = len(self._value(frame, array))
            return None
        if op == "NEWOBJ":
            _, class_name, target = inst
            frame.regs[str(target)] = {"__class__": str(class_name)}
            return None
        if op == "GETFIELD":
            _, obj, field_name, target = inst
            frame.regs[str(target)] = self._value(frame, obj).get(
                str(field_name), 0
            )
            return None
        if op == "SETFIELD":
            _, source, obj, field_name = inst
            self._value(frame, obj)[str(field_name)] = self._value(
                frame, source
            )
            return None
        raise IRRuntimeError(f"Instrucción no soportada: {inst}")

    def _value(self, frame: Frame, operand: object) -> Any:
        if isinstance(operand, str):
            if operand in frame.regs:
                return frame.regs[operand]
            if operand in frame.locals:
                return frame.locals[operand]
            if operand in self.globals:
                return self.globals[operand]
        return operand

    def _load_var(self, frame: Frame, name: str) -> Any:
        if name in frame.locals:
            return frame.locals[name]
        return self.globals.get(name, 0)

    def _store_var(self, frame: Frame, name: str, value: Any) -> None:
        if name in frame.locals:
            frame.locals[name] = value
        elif name in self.globals:
            self.globals[name] = value
        else:
            frame.locals[name] = value

    def _arithmetic(self, op: str, a: Any, b: Any) -> Any:
        if op.startswith("ADD"):
            return a + b
        if op.startswith("SUB"):
            return a - b
        if op.startswith("MUL"):
            return a * b
        if op.startswith("DIV"):
            return int(a / b) if op.endswith("I") else a / b
        if op.startswith("MOD"):
            return a % b
        if op.startswith("POW"):
            return a**b
        raise IRRuntimeError(f"Operación no soportada: {op}")


_GLOBAL_OPS = {"VARI", "VARF", "VARB", "VARS", "VARREF"}
_CONTROL_PREFIXES = ("if_", "while_", "for_", "cond_")
_ARITHMETIC = {
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
}


def _tuples(program: IRResult | list[tuple]) -> list[tuple[object, ...]]:
    if isinstance(program, IRResult):
        return program.to_tuples()
    return [tuple(inst) for inst in program]


def _is_function_label(label: str) -> bool:
    return not label.startswith(_CONTROL_PREFIXES)


def _is_param(inst: tuple[object, ...]) -> bool:
    return bool(inst and str(inst[0]).startswith("PARAM"))


def _default_for_op(op: str) -> Any:
    return (
        0.0
        if op.endswith("F")
        else None
        if op.endswith("S") or op.endswith("REF")
        else 0
    )


def _coerce_literal(op: str, value: object) -> Any:
    if op == "MOVF":
        return float(value)  # type: ignore[arg-type]
    if op in {"MOVI", "MOVB"}:
        return int(value)  # type: ignore[arg-type]
    return value


def _compare(op: str, a: Any, b: Any) -> bool:
    return {
        "==": a == b,
        "!=": a != b,
        "<": a < b,
        "<=": a <= b,
        ">": a > b,
        ">=": a >= b,
    }[op]


__all__ = ["Frame", "IRInterp", "IRInterpreter", "IRRuntimeError"]

IRInterp = IRInterpreter
