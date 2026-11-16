# Contributing to Sable

Thanks for helping. Sable is small on purpose, and contributions that keep it
small and understandable are the most valuable.

## Ground rules

- Read `CODE_OF_CONDUCT.md`.
- Keep pull requests focused.
- Add tests for behavior changes.
- `sable.py` stays standard-library only.
- Be honest about limitations; do not market unfinished features.

## Run the tests

```
python3 -m unittest discover -s tests -v
python3 tools/fuzz_parser.py
```

The native VM tests are skipped when no C compiler is available.

## Project layout

- `sable.py` — lexer, parser, checker, interpreter, CLI
- `stdlib/` — small libraries written in Sable
- `examples/` — sample programs
- `tests/` — unittest suite
- `native/` — bytecode compiler and C VM for the core
- `selfhost/` — core interpreter written in Sable

## Good first issues

- Add an example that solves a real small task.
- Improve an error message.
- Add a builtin with tests.
- Pick a milestone from `native/PLAN.md`.

## Pull requests

- Explain what changed and why.
- Include the test command you ran.
- Keep the diff readable.
