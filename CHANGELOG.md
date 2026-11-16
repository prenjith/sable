# Changelog

## 0.13.0 — 2026-11-16

- Native stack bytecode compiler (`native/compiler.py`)
- Native C VM (`native/vm.c`) for the core language
- Native VM tests and `make native` target

## 0.12.0 — 2026-11-16

- Self-hosted core interpreter written in Sable (`selfhost/sable.sable`)
- `read_file` and `argv` builtins for self-hosting
- Self-host parity tests

## 0.11.0 — 2026-11-16

- User research kit for Hack Club sessions: protocol, task cards, consent and
  assent templates, survey, observation rubric, CSV template, and analysis
- Synthetic sample session data and report generation

## 0.10.0 — 2026-11-16

- Browser playground via Pyodide, published with GitHub Pages
- Browser and mobile instructions

## 0.9.0 — 2026-11-16

- Sable → C compiler (`sablec.py`) for the core language
- Native backend tests
- Nuitka-built full-language native binaries in CI releases

## 0.8.0 — 2026-11-16

- Installable Python package with `sable` and `sable-lsp` entry points
- Dockerfile
- GitHub Actions test matrix and standalone binary builds for Linux, macOS,
  and Windows
- Tagged releases attach the built binaries

## 0.7.0 — 2026-11-16

- `--verify` static checks for control flow, unreachable code, duplicate map
  keys, and unreachable match arms
- Seeded property tests
- Parser and checker fuzzer
- Makefile targets for test, fuzz, and verify

## 0.6.0 — 2026-11-15

- Minimal language server (`lsp.py`) with parse and type diagnostics
- Language server test coverage

## 0.5.0 — 2026-11-15

- `spawn`, `wait`, and `sleep` for thread-based concurrency

## 0.4.0 — 2026-11-15

- Classes with methods, `this`, and `new`
- `init` constructors and object field access

## 0.3.0 — 2026-11-15

- Optional type annotations and a static checker (`--check`)
- `import` statements with module caching
- Maps accept strings, numbers, booleans, and nil as keys
- `stdlib/result.sable` and `stdlib/option.sable`
- New examples for types, modules, results, and options

## 0.2.0 — 2026-11-15

- Map dot access (`user.name`, `user.age += 1`)
- `const` declarations
- `try` / `catch` / `throw`
- `match` statements with literal, wildcard, and binding patterns
- `|>` pipeline operator, including piping into calls
- Standard library additions: `map`, `filter`, `reduce`, `sum`, `min`, `max`,
  `abs`, `floor`, `ceil`, `round`, `sqrt`, `pow`, `contains`, `index_of`,
  `slice`, `replace`, `trim`, `starts_with`, `ends_with`
- Optional comparator for `sort`
- Documentation site and VS Code syntax highlighting

## 0.1.0 — 2026-11-13

- Initial release: lexer, parser, tree-walking interpreter, environments,
  closures, lists, maps, builtins, REPL, and tests
