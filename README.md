<p align="center">
  <img src="logo.svg" width="96" alt="Sable logo">
</p>

<h1 align="center">Sable</h1>

<p align="center">
  A small scripting language with closures, pattern matching, error handling,
  and a pipeline operator. Learn it in an afternoon and ship a real script.
</p>

<p align="center">
  <a href="https://pranavrenjith2-source.github.io/sable-playground/">Playground</a> ·
  <a href="https://github.com/prenjith/sable/releases">Download</a> ·
  <a href="docs/index.html">Reference</a>
</p>

Sable is a tree-walking interpreter written in Python with no third-party
dependencies. It is meant for small scripts, experiments, and learning how a
language fits together.

## Features

- C-like syntax with semicolon-terminated statements
- `let` and `const` declarations with block scoping
- Optional type annotations and a static checker (`--check`)
- `import` statements with module caching
- First-class functions, anonymous functions, and lexical closures
- Classes with methods, `this`, and `new`
- Concurrent tasks with `spawn`, `wait`, and `sleep`
- Full-language native binaries built with Nuitka
- Browser playground via Pyodide, published with GitHub Pages
- Self-hosted core interpreter written in Sable
- Native stack bytecode compiler and C VM for the core language
- Practical file, JSON, environment, random, and clock builtins
- `--test` runner for `.sable` test files
- Lists and maps with string, number, boolean, or nil keys
- `map.key` dot access for string keys
- `if` / `else`, `while`, and `for ... in`
- `match` statements with literal, wildcard, and binding patterns
- `try` / `catch` / `throw`
- `|>` pipelines
- A standard library for math, strings, and collections
- REPL, file runner, token dumper, AST dumper, and type checker
- Static verification (`--verify`) and a parser/checker fuzzer
- Errors with line and column information

## Install

With Python 3.9+:

```
pip install .
sable examples/fizzbuzz.sable
```

Or run the single file directly:

```
python3 sable.py examples/fizzbuzz.sable
python3 sable.py examples/fib.sable
python3 sable.py            # REPL
python3 sable.py --tokens examples/fib.sable
python3 sable.py --ast examples/fib.sable
python3 sable.py --check examples/types.sable
python3 sable.py --verify examples/types.sable
python3 sable.py --test tests_dir
```

Docker:

```
docker build -t sable .
docker run --rm -v "$PWD:/work" -w /work sable examples/fizzbuzz.sable
```

GitHub Actions builds standalone `sable` binaries for Linux, macOS, and
Windows; tagged releases attach them.

## Run it anywhere

- Browser: https://pranavrenjith2-source.github.io/sable-playground/ (Pyodide; works on
  phones and tablets)
- Linux, macOS, Windows: standalone binaries on the
  [releases page](https://github.com/prenjith/sable/releases)
- Android (Termux): `pkg install python`, then
  `pip install git+https://github.com/prenjith/sable.git`
- iOS: run `sable.py` in Pythonista or a-Shell
- Docker: see the Dockerfile above

Threads are not available in the browser build.

Sable programs use the `.sable` extension. Comments are `// line` and
`/* block */`.

## A quick tour

```sable
let name = "world";
print("hello, " + name);

fn add(a, b) {
    return a + b;
}

let nums = [1, 2, 3];
let total = 0;
for n in nums {
    total = total + n;
}
print(total);
```

Functions close over the scope where they were created:

```sable
fn counter() {
    let n = 0;
    fn next() {
        n = n + 1;
        return n;
    }
    return next;
}

let c = counter();
print(c());
print(c());
```

Maps accept string, number, boolean, or nil keys and support dot access for
string keys:

```sable
let user = {"name": "ana", "age": 15};
print(user.name);
user.age = user.age + 1;
print(user.age);
```

`const` values cannot be reassigned:

```sable
const limit = 10;
limit = 20;   // RuntimeError: cannot assign to constant 'limit'
```

### Type annotations

Annotations are optional. When present, they are checked before the program
runs:

```sable
fn area(width: number, height: number): number {
    return width * height;
}

let w: number = 4;
let h: number = 5;
print(area(w, h));
```

Use `any` to opt out of checking. `python3 sable.py --check file.sable` runs
the checker without executing the program.

`match` picks the first arm that fits:

```sable
fn describe(n) {
    match n {
        1 => return "one";
        2 => return "two";
        _ => return "many";
    }
}
```

Errors can be thrown and caught:

```sable
try {
    if b == 0 {
        throw "cannot divide by zero";
    }
    print(a / b);
} catch err {
    print("error: " + str(err));
}
```

Runtime errors arrive as maps with `message` and `line` fields. Thrown values
are passed through unchanged.

Pipelines pass a value into a function:

```sable
let result = nums
    |> filter(is_even)
    |> map(square);

print(result);
```

`value |> f` calls `f(value)`. If the right side is a call, the value becomes
the first argument: `value |> f(x)` is `f(value, x)`.

## Modules

```sable
import "mathx.sable";

print(square(5));
```

Imports are resolved relative to the importing file and run once. Everything
defined by the imported file is available in the importing program.

## Classes

Classes hold fields and methods. `this` refers to the current object, and
`new` runs `init` if it exists:

```sable
class Point {
    fn init(x, y) {
        this.x = x;
        this.y = y;
    }

    fn length() {
        return sqrt(this.x * this.x + this.y * this.y);
    }
}

let p = new Point(3, 4);
print(p.length());
```

## Concurrency

`spawn` runs a function on its own thread and returns a task. `wait` joins the
task and returns its result:

```sable
let task = spawn(fn() {
    return 21 * 2;
});

print(wait(task));
```

`sleep(ms)` pauses the current task. Threads share memory, so keep tasks
independent or synchronize access yourself.

## Native VM

`native/compiler.py` compiles the core language to stack bytecode and
`native/vm.c` runs it with no Python runtime:

```
python3 native/compiler.py examples/fizzbuzz.sable -o /tmp/fizzbuzz.sasm
cc -O2 -o native/sable-vm native/vm.c -lm
./native/sable-vm /tmp/fizzbuzz.sasm
```

It supports numbers, strings, booleans, nil, variables, arithmetic,
comparisons, if/else, while, and print. Functions, lists, maps, classes,
errors, modules, and threads are the next milestones in `native/PLAN.md`.

## Useful scripts

`examples/todo.sable` is a small JSON-backed todo CLI:

```
python3 sable.py examples/todo.sable add "buy milk"
python3 sable.py examples/todo.sable list
python3 sable.py examples/todo.sable done 0
python3 sable.py examples/todo.sable clear
```

`stdlib/testing.sable` provides `assert_eq`, `assert_true`, and `assert_false`.
`sable --test dir` runs every `.sable` file in a directory and reports pass or
fail.

## Self-hosting

`selfhost/sable.sable` is a core Sable interpreter written in Sable. Run it
with the host:

```
python3 sable.py selfhost/sable.sable examples/fizzbuzz.sable
```

It supports the core language and is covered by parity tests. The first run
still needs a seed interpreter; the path to a fully native build is extending
the C backend to the features the self-hosted interpreter uses.

## Types

- `nil`
- `bool`: `true`, `false`
- `number`: all numbers are floats, printed without a trailing `.0` when whole
- `string`
- `list`
- `map` (string keys)
- functions and builtins

Only `nil` and `false` are false. `0` and `""` are true.

## Operators

`+ - * / %` work on numbers; `+` also concatenates strings and lists.

`== != < <= > >=` compare values. `and` and `or` short-circuit and return one
of their operands. `not` is a unary operator.

Assignment is `=`, with `+=`, `-=`, `*=`, and `/=` as shortcuts.

## Builtins

| Name | Description |
| --- | --- |
| `print(...)` | Write values to stdout |
| `len(x)` | Length of a string, list, or map |
| `str(x)`, `num(x)`, `type(x)` | Conversions and type names |
| `range(a, b?, step?)` | List of numbers |
| `push(list, value)`, `pop(list)` | List mutation |
| `keys(map)`, `has(map, key)` | Map helpers |
| `map(list, fn)`, `filter(list, fn)`, `reduce(list, fn, initial?)` | Higher-order list operations |
| `sort(list, comparator?)` | Sorted copy, optionally with a comparator |
| `sum(list)`, `min(...)`, `max(...)`, `abs(n)` | Numeric helpers |
| `floor(n)`, `ceil(n)`, `round(n)`, `sqrt(n)`, `pow(a, b)` | Math helpers |
| `contains(x, value)`, `index_of(x, value)`, `slice(x, start, end?)` | Search and slicing |
| `replace(s, old, new)`, `trim(s)`, `starts_with(s, p)`, `ends_with(s, s2)` | String helpers |
| `join(list, sep)`, `split(s, sep)`, `upper(s)`, `lower(s)` | String conversion |
| `input(prompt?)`, `assert(cond, message?)` | Input and checks |
| `read_file`, `write_file`, `append_file` | File I/O |
| `file_exists`, `list_dir` | Filesystem checks |
| `getenv`, `argv()` | Environment and arguments |
| `json_encode`, `json_decode` | JSON conversion |
| `clock`, `random`, `random_int` | Time and randomness |
| `exit(code)` | Exit status |
| `spawn(fn, ...)`, `wait(task)`, `sleep(ms)` | Concurrency |

## Project layout

```
sable.py                 interpreter, parser, lexer, checker, and CLI
selfhost/                core interpreter written in Sable
native/                  bytecode compiler and C VM for the core
pyproject.toml           pip packaging and entry points
Dockerfile               container image
.github/workflows/       cross-platform tests and binary builds
tools/fuzz_parser.py     parser and checker fuzzer
Makefile                 test, fuzz, and verify shortcuts
stdlib/                  small libraries written in Sable
examples/                sample programs
tests/                   unittest suite
docs/index.html          language reference page
editors/vscode/          syntax highlighting extension
```

## Development

```
python3 -m unittest discover -s tests -v
```

The design simulation is in `tools/simulate_bots.py`; its results are written
up in `docs/simulation.md`.

The interpreter is a single file. The lexer produces tokens with line and
column positions, the parser builds an AST with recursive descent, and the
interpreter evaluates that AST against a chain of environments. Closures
capture their defining environment, and `return`, `break`, and `continue` are
control-flow signals.

## Verification

`--verify` runs the type checker plus extra static checks:

```
python3 sable.py --verify examples/types.sable
python3 sable.py --test tests_dir
```

It reports break/continue outside loops, return outside functions, unreachable
code, duplicate map keys, and unreachable match arms. The test suite also
includes seeded property tests, and `tools/fuzz_parser.py` fuzzes the lexer,
parser, and checker:

```
python3 -m unittest discover -s tests
python3 tools/fuzz_parser.py
```

This is practical verification, not formal proof.

## Rough edges

- The native VM covers the core language only.
- Threads have no synchronization primitives.
- There is no package ecosystem.
- The docs are better than the test coverage in a few corners.

## Why I built this

I wanted a language small enough to read in one sitting, with the features I
actually use in small scripts. It started as a parser experiment and grew from
there. The playground exists so nobody has to install anything to try it.

## Limitations

- No inheritance or interfaces.
- Threads share memory; there is no locking or async/await.
- No bytecode compiler yet; the evaluator is a tree-walker.
- Formal verification is not included; `--verify`, property tests, and the
  fuzzer are practical checks.
- No garbage collector concerns (it is Python under the hood).
- `and` / `or` return operand values, not strict booleans.

## License

MIT. See `LICENSE`.
