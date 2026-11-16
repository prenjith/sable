#!/usr/bin/env python3
"""Fuzz the lexer, parser, and checker with random token sequences."""

import os
import random
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sable

TOKENS = [
    "let", "const", "fn", "if", "else", "while", "for", "in", "return",
    "break", "continue", "try", "catch", "throw", "match", "import",
    "class", "new", "this", "true", "false", "nil", "and", "or", "not",
    "x", "y", "foo", "bar", "_",
    "0", "1", "2", "3.5", '"s"', '""',
    "+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=",
    "=", "+=", "-=", "*=", "/=", "=>", "|>", ".",
    "(", ")", "{", "}", "[", "]", ",", ":", ";",
]


def main():
    rng = random.Random(2026)
    cases = 3000
    for index in range(cases):
        length = rng.randint(1, 40)
        source = " ".join(rng.choice(TOKENS) for _ in range(length))
        try:
            program = sable.parse(source)
            sable.Checker().check(program)
        except sable.SableError:
            continue
        except Exception:
            print("crash on case", index)
            print(source)
            traceback.print_exc()
            return 1
    print(f"fuzz ok ({cases} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
