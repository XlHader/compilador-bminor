from .formatting import format_instruction, format_ir
from .generator import generate_ir
from .models import (
    IRDiagnostic,
    IRInstruction,
    IRResult,
    LabelGenerator,
    RegisterGenerator,
)
from .opcodes import (
    alloc_opcode,
    load_opcode,
    param_opcode,
    print_opcode,
    store_opcode,
    type_suffix,
    var_opcode,
)
from .optimizer import IROptimizer, optimize_ir

__all__ = [
    "IRDiagnostic",
    "IRInstruction",
    "IROptimizer",
    "IRResult",
    "LabelGenerator",
    "RegisterGenerator",
    "alloc_opcode",
    "format_instruction",
    "format_ir",
    "generate_ir",
    "load_opcode",
    "optimize_ir",
    "param_opcode",
    "print_opcode",
    "store_opcode",
    "type_suffix",
    "var_opcode",
]
