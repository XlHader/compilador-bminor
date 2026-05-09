## 1. IR Package Foundation

- [x] 1.1 Create `src/proyect/ir/` with public exports for IR models, generation, and formatting.
- [x] 1.2 Define typed IR instruction, diagnostic, and result models with tuple-compatible conversion.
- [x] 1.3 Define opcode constants and type-family helpers for integer, float, boolean, char/byte, string, references, arrays, and objects.
- [x] 1.4 Add deterministic register and label generation utilities.
- [x] 1.5 Add unit tests for IR model construction, tuple conversion, and text formatting.

## 2. Generator Core

- [x] 2.1 Implement `generate_ir(program, semantic_result)` with validation that semantic analysis succeeded before lowering.
- [x] 2.2 Implement generator state for instructions, diagnostics, current function/class context, registers, labels, and semantic metadata lookup.
- [x] 2.3 Implement value/place abstractions for identifiers, array elements, and object fields.
- [x] 2.4 Add tests for semantic-result rejection and deterministic empty/simple program behavior.

## 3. Primitive Values and Variables

- [x] 3.1 Lower integer, float, boolean, char, and string literals into typed load instructions.
- [x] 3.2 Lower unary, binary, comparison, boolean, and string operations into typed three-address instructions.
- [x] 3.3 Lower global/local variable declarations, allocations, initializers, loads, stores, and parameters.
- [x] 3.4 Lower simple and compound assignments through the place abstraction.
- [x] 3.5 Add tests for primitive expressions, string expressions, declarations, and assignments.

## 4. Statements and Control Flow

- [x] 4.1 Lower blocks, expression statements, print statements, and return statements.
- [x] 4.2 Lower `if` statements with labels, conditional branches, optional else blocks, and joins.
- [x] 4.3 Lower `while` loops with condition, body, back edge, and exit labels.
- [x] 4.4 Lower `for` loops preserving initializer, condition, body, update, and exit evaluation order.
- [x] 4.5 Lower ternary expressions using branch labels and `PHI` join values.
- [x] 4.6 Add tests for statement lowering and control-flow instruction order.

## 5. Functions, Calls, and Methods

- [x] 5.1 Lower function declarations into function labels/headers, parameter setup, body instructions, and explicit return paths.
- [x] 5.2 Lower direct function calls with left-to-right argument evaluation and return destinations for non-void calls.
- [x] 5.3 Lower class method declarations using qualified names.
- [x] 5.4 Lower member method calls by passing the receiver object as the first call argument.
- [x] 5.5 Add tests for functions, void/non-void returns, direct calls, and method calls.

## 6. Arrays and Indexing

- [x] 6.1 Lower array type declarations and array reference storage.
- [x] 6.2 Lower array initializers by allocating arrays and storing elements in order.
- [x] 6.3 Lower index expressions as values using array load instructions.
- [x] 6.4 Lower index expressions as assignment targets using array store instructions.
- [x] 6.5 Lower `array_length` as the `ALENGTH` intrinsic instruction.
- [x] 6.6 Add tests for array initialization, reads, writes, nested expressions, and `array_length`.

## 7. Objects and Member Access

- [x] 7.1 Lower class declarations enough to register field and method layout metadata for IR generation.
- [x] 7.2 Lower `new ClassName(...)` with `NEWOBJ` and optional `ClassName.init` call.
- [x] 7.3 Lower member field reads with `GETFIELD`.
- [x] 7.4 Lower member field assignments with `SETFIELD`.
- [x] 7.5 Add tests for object construction, field reads/writes, constructor arguments, and method receiver lowering.

## 8. CLI and Documentation

- [x] 8.1 Add an explicit CLI option for IR output while preserving current default tree, Graphviz, error, and exit-code behavior.
- [x] 8.2 Print deterministic IR output from the CLI only after parse and semantic success.
- [x] 8.3 Update README with Proyecto 4 status, IR commands, opcode set, extensions, and examples.
- [x] 8.4 Add CLI tests for successful IR output and failure cases where IR must not print.

## 9. Regression and Verification

- [x] 9.1 Add source-to-IR integration tests using representative `examples/` programs.
- [x] 9.2 Ensure existing lexer, parser, semantic, AST visualizer, and CLI tests still pass.
- [x] 9.3 Run `pytest` and fix any regressions.
- [x] 9.4 Run `ruff check .` and `ruff format --check .` and fix any reported issues.
- [x] 9.5 Validate at least one documented CLI command: `PYTHONPATH=src python -m proyect.main examples/parser.bp --ir`.
