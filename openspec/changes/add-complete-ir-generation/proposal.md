## Why

Proyecto 4 requires the compiler to lower the existing BMinor AST into an intermediate three-address, SSA-style machine code representation. The current project stops at parsing, AST visualization, and semantic validation, so there is no executable compiler backend path for primitives, control flow, arrays, objects, indexes, members, or calls.

## What Changes

- Add a complete IR generation capability that runs after successful parsing and semantic analysis.
- Introduce IR models for typed three-address instructions, SSA temporaries, labels, and structured output.
- Implement an AST visitor/lowering pass that supports primitive values, strings, arrays, objects/classes, index expressions, member expressions, function and method calls, constructors, assignments, print, return, conditionals, loops, and ternary expressions.
- Extend the project IR instruction set where the assignment's base opcodes are insufficient, especially for arrays, object fields, strings, allocation, and runtime intrinsics.
- Update the CLI to expose IR output without breaking the existing parse tree and Graphviz behavior.
- Update README documentation with the new compiler phase, CLI usage, supported IR instructions, and examples.

## Capabilities

### New Capabilities
- `ir-generation`: Complete lowering from semantically valid BMinor AST to typed three-address SSA-style IR, including primitives, strings, arrays, objects, index/member access, calls, constructors, control flow, CLI output, and documentation.

### Modified Capabilities
- None.

## Impact

- Adds a new compiler backend package under `src/proyect/` for IR models and generation.
- Integrates with `src/proyect/main.py` after `parse_bminor` and `analyze_semantic` succeed.
- Depends on existing parser AST models and semantic `node_types` / `resolved_symbols` maps to avoid duplicate type inference.
- Adds or updates tests for IR generation, CLI IR output, and README-covered examples.
- Updates README to describe Proyecto 4 behavior and commands.
