# Building a small language in public: what I learned from Sable

Sable is a small scripting language with a hand-written lexer, parser, checker,
interpreter, a self-hosted core, and a C bytecode VM.

## What worked

- A browser playground removed the install step.
- Optional type annotations caught real mistakes without forcing static typing.
- Pattern matching and pipelines made examples shorter.
- A test runner and a small stdlib made the language feel usable.

## What did not

- The native backend is a subset, and that confuses people.
- Concurrency without synchronization primitives is a trap.
- Marketing a language before it has an ecosystem is hard.

## What is next

- Functions, collections, and errors in the native VM
- More real examples
- Feedback from Hack Club sessions

Playground and source links at the end.
