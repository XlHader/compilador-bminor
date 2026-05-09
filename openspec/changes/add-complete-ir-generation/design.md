## Context

The project currently implements the BMinor frontend: lexer, parser, AST models, AST visualization, semantic models, symbol tables, type checking, and CLI reporting. Proyecto 4 adds the next compiler phase: lowering a semantically valid AST into a deterministic three-address, SSA-style intermediate representation.

The existing semantic phase is the correct source of truth for types and bindings. `SemanticResult.node_types` identifies the semantic type of expressions, and `SemanticResult.resolved_symbols` binds identifiers, members, calls, classes, and variables. IR generation should consume those maps instead of duplicating type inference.

The assignment's base instruction set covers primitive integer, float, and byte operations plus labels, branches, calls, and returns. The current BMinor language supports more than that: booleans, chars, strings, arrays, class types, object construction, member access, indexing, functions, methods, loops, ternaries, and builtins such as `array_length`. Complete support therefore requires a documented project-level IR extension for arrays, objects, strings, and SSA joins.

## Goals / Non-Goals

**Goals:**
- Add a new IR package with typed instruction models, IR result objects, register/label generation, and readable formatting.
- Generate IR only after parse and semantic success.
- Lower the full current AST surface: declarations, functions, classes, variables, blocks, expression statements, print, return, if, while, for, literals, identifiers, unary/binary expressions, assignments, calls, indexing, member access, object creation, array initialization, and ternary expressions.
- Support primitive, boolean, char/byte, string, array, class/object, function, and void-related lowering decisions.
- Preserve SSA-style virtual temporaries: each generated temporary register is assigned once.
- Expose CLI IR output with a dedicated option while preserving current tree, Graphviz, and error behavior.
- Update README and tests for the new phase.

**Non-Goals:**
- Execute the IR in a VM or emit native machine code.
- Add optimizations such as constant folding, dead-code elimination, register allocation, or data-flow optimization.
- Change lexer/parser grammar unless tests reveal an existing parser bug that blocks IR coverage.
- Replace the semantic analyzer or alter its public behavior except where metadata gaps are discovered during implementation.
- Implement inheritance, dynamic dispatch, garbage collection, or object layout beyond the current class/member model.

## Decisions

### 1. Add `proyect.ir` as a separate compiler phase

Create a focused package, likely:

```text
src/proyect/ir/
├─ __init__.py
├─ models.py       # IRInstruction, IRResult, IRDiagnostic, helpers
├─ generator.py    # generate_ir(program, semantic_result)
├─ formatting.py   # deterministic text rendering
└─ opcodes.py      # opcode constants / type suffix mapping
```

This keeps IR separate from parser and semantic code. The parser continues to build syntax, semantic analysis continues to validate meaning, and IR generation becomes a consumer of both.

Alternative considered: add IR methods directly to AST classes. Rejected because the existing AST is a clean immutable syntax model and should not know backend details.

### 2. Use semantic metadata for all type and symbol decisions

IR generation will require a successful `SemanticResult`. The generator will read:
- `node_types[id(node)]` for expression result types.
- `resolved_symbols[id(node)]` for identifiers, members, callees, constructors, and declarations.
- class member maps for fields and methods.

This avoids parallel type inference and keeps errors centralized in the semantic phase.

Alternative considered: infer types inside IR generation. Rejected because it risks inconsistent behavior and duplicates already-tested semantic logic.

### 3. Represent IR as tuple-compatible structured instructions

The assignment asks for tuples such as `(operation, operands..., destination)`. Internally, use a small dataclass for readability and formatting, while exposing tuple conversion for tests and project expectations.

Example conceptual shape:

```text
IRInstruction(op="ADDI", args=("R1", "R2", "R3"))
tuple form: ("ADDI", "R1", "R2", "R3")
```

Alternative considered: raw tuples everywhere. Rejected because object/string/array extensions and diagnostics are easier to test and maintain with named fields plus tuple conversion.

### 4. Keep SSA for temporaries and mutable storage for variables

Every generated temporary register is assigned once (`R1`, `R2`, ...). Variables, array elements, and object fields remain mutable storage locations accessed through `LOAD*`/`STORE*`, array load/store, and field load/store instructions.

This matches the assignment's examples, which use SSA registers but still store into variables by name.

For branch expression joins, add a `PHI` instruction only where a value must be selected from multiple predecessor labels, especially ternary expressions.

Alternative considered: pure SSA for all variables with full dominance analysis. Rejected as too large for this project and unnecessary for the specified tuple IR output.

### 5. Split lowering into value and place paths

Some expressions can be used both as values and assignment targets. The generator should separate:

```text
emit_value(expr) -> register
emit_place(expr) -> assignable place
store_place(place, source_register)
load_place(place) -> register
```

Places include:
- `VariablePlace(name, semantic_type)`
- `ArrayElementPlace(array_register, index_register, element_type)`
- `FieldPlace(object_register, field_name, field_type, class_name)`

This is essential for `x`, `arr[i]`, and `obj.field` in both read and assignment contexts.

### 6. Type mapping and base opcodes

Use existing base opcodes for assignment-compatible primitive machine types:

| BMinor semantic type | IR family |
|---|---|
| `integer` | `I` opcodes (`MOVI`, `ADDI`, `LOADI`, `STOREI`, `PRINTI`) |
| `float` | `F` opcodes (`MOVF`, `ADDF`, `LOADF`, `STOREF`, `PRINTF`) |
| `char` | `B` opcodes (`MOVB`, `LOADB`, `STOREB`, `PRINTB`) |
| `boolean` | integer-compatible `0`/`1` results plus `CMPI`, `AND`, `OR`, `XOR` |
| `string` | project extension `S` opcodes |
| arrays/classes | reference opcodes |

Conversions use base instructions where available (`ITOF`, `FTOI`, `BTOI`, `ITOB`) only if the semantic layer allows the conversion or an explicit lowering case needs it.

### 7. Document project-level extended opcodes

Add extensions for features unsupported by the assignment's base virtual machine:

```text
; strings
MOVS value, target
LOADS name, target
STORES source, name
CONCATS r1, r2, target
CMPS op, r1, r2, target
PRINTS source

; references / arrays
VARREF name
ALLOCREF name
LOADREF name, target
STOREREF source, name
NEWARRAY element_type, length, target
ARRAYINIT element_type, length, target
ALOAD array, index, target
ASTORE source, array, index
ALENGTH array, target

; objects/classes
NEWOBJ class_name, target
GETFIELD object, field_name, target
SETFIELD source, object, field_name

; SSA/control support
PHI incoming_pairs, target
```

Existing `CALL`, `RET`, `LABEL`, `BRANCH`, and `CBRANCH` remain the control-flow foundation. Methods lower to direct calls using a qualified name and receiver argument:

```text
CALL ClassName.method, self, arg0, ..., target
```

### 8. Lower functions, methods, and constructors consistently

Function declarations emit a deterministic function label/header followed by parameter setup and body instructions. Void functions get an explicit `RET` path if needed.

Class methods are emitted as qualified functions. The object receiver is passed as an implicit first argument for member calls.

Object construction lowers to:

```text
NEWOBJ ClassName, Rn
CALL ClassName.init, Rn, arg0, ..., _
```

If a class has no `init`, allocation alone produces the object reference.

### 9. Lower arrays as reference values

Array variables hold references. Array initializers allocate an array of known length, then store each element in order. Index expressions evaluate the array and index left-to-right. `array_length` lowers to `ALENGTH` instead of a normal user function call.

This keeps arrays usable as values, parameters, fields, and local variables without inventing full pointer arithmetic.

### 10. CLI integration is opt-in

Add a dedicated CLI flag such as `--ir`. Current default behavior remains parse success plus tree output unless disabled. With `--ir`, the CLI runs IR generation after semantic success and prints deterministic text output. Existing parse, semantic, missing-file, `--tree`, `--no-tree`, and `--graphviz` behavior must remain stable.

### 11. Test from the outside inward

Testing should start with model/formatting snapshots, then generator units for expressions and statements, then integration tests from source text through parser/semantic/IR, and finally CLI tests. Existing parser and semantic tests should remain unchanged except where they need new helper coverage.

## Risks / Trade-offs

- [Risk] The base assignment opcodes do not cover full current BMinor semantics → Mitigation: document explicit project-level extensions in README and tests.
- [Risk] IR generation can duplicate semantic logic accidentally → Mitigation: require `SemanticResult` and treat missing `node_types` or `resolved_symbols` entries as IR diagnostics or implementation errors.
- [Risk] Method calls and constructors may be ambiguous without runtime object semantics → Mitigation: use direct qualified dispatch and receiver-as-first-argument; do not introduce inheritance or vtables.
- [Risk] Ternary expressions and branch joins complicate SSA → Mitigation: keep SSA limited to temporaries and use `PHI` only for expression joins.
- [Risk] Arrays and objects need runtime behavior that is not executable yet → Mitigation: define IR representation only; VM execution is explicitly out of scope.
- [Risk] CLI output snapshots can become brittle → Mitigation: make formatting deterministic and test key instruction sequences rather than incidental whitespace where possible.

## Migration Plan

1. Add the IR package and tests without changing default CLI behavior.
2. Integrate `--ir` into the CLI after parse and semantic success.
3. Update README with the new phase, opcode extensions, and commands.
4. Keep rollback simple: removing `--ir` integration should leave lexer, parser, semantic analysis, tree output, and Graphviz behavior untouched.

## Open Questions

- Exact CLI flag name can be finalized during implementation; `--ir` is the proposed default.
- Exact textual formatting can be adjusted to match course expectations if sample output files exist outside the current repository.
- If tests require strict tuple shape for every instruction, the dataclass model must expose that tuple shape directly and consistently.
