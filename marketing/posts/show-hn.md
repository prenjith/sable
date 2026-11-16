Show HN: Sable – a small scripting language with a browser playground

I built Sable, a small dynamically typed language. It has a lexer, parser, type
checker, tree-walking interpreter, a self-hosted core interpreter written in
Sable, and a C bytecode VM for the core language.

It supports classes, closures, pattern matching, pipelines, try/catch, modules,
and thread-based concurrency. There is a zero-install browser playground, and
native binaries for Linux, macOS, and Windows.

The goal is a language you can learn in an afternoon and use for small scripts:
file and JSON work, automation, and teaching.

Playground: https://pranavrenjith2-source.github.io/sable-playground/
Repo: https://github.com/prenjith/sable

I would love feedback on the syntax, the error messages, and what would make it
useful for a first project. The self-hosted core and the native VM are the parts
I am least sure about.
