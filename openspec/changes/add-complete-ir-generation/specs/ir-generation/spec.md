## ADDED Requirements

### Requirement: IR generation entrypoint
The compiler SHALL provide a programmatic IR generation entrypoint that accepts a semantically valid `Program` AST and its `SemanticResult`, then returns an ordered IR result containing instructions, labels, diagnostics, and generated temporaries.

#### Scenario: Generate IR after successful semantic analysis
- **WHEN** a BMinor source file parses successfully and semantic analysis returns no errors
- **THEN** the IR entrypoint returns a successful IR result with a deterministic instruction sequence

#### Scenario: Reject invalid semantic input
- **WHEN** semantic analysis contains one or more errors
- **THEN** IR generation MUST NOT produce executable instructions and MUST report that IR requires a semantically valid program

### Requirement: Primitive and string expression lowering
The IR generator SHALL lower integer, float, boolean, char, byte-compatible char, and string literals and operations into typed three-address instructions using SSA-style temporaries.

#### Scenario: Lower primitive arithmetic
- **WHEN** an expression contains valid integer or float arithmetic
- **THEN** the generator emits typed arithmetic instructions such as `ADDI`, `SUBI`, `MULI`, `DIVI`, `ADDF`, `SUBF`, `MULF`, and `DIVF` with one assigned destination per temporary

#### Scenario: Lower comparisons and boolean operations
- **WHEN** an expression contains comparisons or boolean operators
- **THEN** the generator emits comparison or logical instructions that materialize boolean results as integer-compatible `0` or `1` temporaries

#### Scenario: Lower string operations
- **WHEN** an expression contains supported string literals, equality, inequality, concatenation, or print operations
- **THEN** the generator emits string-specific IR instructions for loading, comparing, concatenating, and printing strings

### Requirement: Variable declaration and assignment lowering
The IR generator SHALL lower global variables, local variables, parameters, assignments, and compound assignments using typed storage instructions and expression temporaries.

#### Scenario: Lower variable declaration with initializer
- **WHEN** a variable declaration has an initializer
- **THEN** the generator emits a typed declaration or allocation instruction followed by a typed store of the initializer value

#### Scenario: Lower compound assignment
- **WHEN** a valid compound assignment such as `x += y` or `arr[i] *= y` is encountered
- **THEN** the generator loads the previous lvalue value, emits the typed operation, and stores the new value back to the same lvalue target

### Requirement: Lvalue lowering for identifiers, indexes, and members
The IR generator SHALL distinguish expression values from assignable places for identifiers, array indexes, and object members.

#### Scenario: Load from an indexed array element
- **WHEN** an index expression is used as a value
- **THEN** the generator emits instructions to evaluate the array and index, then emits a typed array load into a new temporary

#### Scenario: Store to an indexed array element
- **WHEN** an index expression is used as an assignment target
- **THEN** the generator emits instructions to evaluate the array, index, and source value, then emits a typed array store

#### Scenario: Load and store object members
- **WHEN** a member expression is used as a value or assignment target
- **THEN** the generator emits field load or field store instructions based on the resolved class member symbol

### Requirement: Array allocation and initialization
The IR generator SHALL lower array types, array initializers, index access, index assignment, and `array_length` into explicit array IR instructions.

#### Scenario: Lower array initializer
- **WHEN** a variable is initialized with an array initializer
- **THEN** the generator allocates an array of the correct element type and length, stores each element in order, and produces the array reference

#### Scenario: Lower array_length intrinsic
- **WHEN** a valid `array_length(array)` call is encountered
- **THEN** the generator emits an array length instruction that writes the length into an integer temporary

### Requirement: Object allocation and member access
The IR generator SHALL lower class declarations, object allocation, constructor calls, fields, methods, and member access into explicit object IR instructions.

#### Scenario: Lower object construction
- **WHEN** a valid `new ClassName(args...)` expression is encountered
- **THEN** the generator emits an object allocation instruction, invokes `ClassName.init` with the new object as `self` when an initializer exists, and returns the object reference temporary

#### Scenario: Lower method call
- **WHEN** a valid method call is encountered through a member expression
- **THEN** the generator emits a direct method call instruction using the resolved class method name and passes the receiver object as the first argument

### Requirement: Function lowering and calls
The IR generator SHALL lower function declarations, parameters, returns, direct function calls, and method calls into labeled IR blocks with explicit call and return instructions.

#### Scenario: Lower function declaration
- **WHEN** a function declaration is processed
- **THEN** the generator emits a function label or header, parameter storage setup, body instructions, and an explicit return path

#### Scenario: Lower function call
- **WHEN** a valid function call expression is encountered
- **THEN** the generator evaluates arguments left-to-right and emits a call instruction with a destination temporary for non-void returns

### Requirement: Control-flow lowering
The IR generator SHALL lower `if`, `while`, `for`, ternary expressions, blocks, `return`, expression statements, and `print` into labels, branches, conditional branches, and typed operations.

#### Scenario: Lower conditional statement
- **WHEN** an `if` statement is encountered
- **THEN** the generator emits labels and conditional branches for then, optional else, and join blocks

#### Scenario: Lower loops
- **WHEN** a `while` or `for` loop is encountered
- **THEN** the generator emits labels and branches that preserve source evaluation order for initialization, condition, body, update, and exit

#### Scenario: Lower ternary expression
- **WHEN** a ternary expression is used as a value
- **THEN** the generator emits branch-based lowering that produces one result temporary for the selected branch value

### Requirement: CLI IR output
The CLI SHALL expose IR generation through an explicit option while preserving existing parse tree, Graphviz, error reporting, and exit-code behavior.

#### Scenario: Print IR from the CLI
- **WHEN** the user runs the CLI with the IR output option on a valid source file
- **THEN** the CLI prints the generated IR in deterministic order and exits with code `0`

#### Scenario: Preserve current error handling
- **WHEN** lexing, parsing, or semantic analysis fails
- **THEN** the CLI reports the existing errors, does not print misleading IR, and exits with the existing failure code

### Requirement: Documentation and examples
The README SHALL document the IR generation phase, supported instruction set, extended opcodes for arrays/objects/strings, CLI usage, and at least one example input-to-IR flow.

#### Scenario: User follows README command
- **WHEN** a user runs the documented IR command against an example BMinor file
- **THEN** the command works with the documented `PYTHONPATH=src python -m proyect.main ...` style and prints IR output

### Requirement: Verification coverage
The project SHALL include tests that cover IR models, expression lowering, lvalue lowering, arrays, objects, calls, control flow, CLI output, and regression examples.

#### Scenario: Run project verification
- **WHEN** `pytest`, `ruff check .`, and `ruff format --check .` are run after implementation
- **THEN** all checks pass without breaking existing lexer, parser, semantic, AST visualizer, or CLI tests
