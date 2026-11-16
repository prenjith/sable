#!/usr/bin/env python3
"""Compile the core of Sable to a simple stack bytecode for the native VM."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sable


class NativeError(Exception):
    pass


def sasm_string(text):
    out = ['"']
    for ch in text:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


class Compiler:
    def __init__(self, program):
        self.program = program
        self.lines = []
        self.counter = 0

    def emit(self, line):
        self.lines.append(line)

    def label(self, prefix):
        self.counter += 1
        return f"{prefix}{self.counter}"

    def compile(self):
        for stmt in self.program.statements:
            self.statement(stmt)
        self.emit("HALT")
        return "\n".join(self.lines)

    def statement(self, stmt):
        if isinstance(stmt, (sable.Let, sable.Const)):
            if stmt.value is None:
                self.emit("PUSH_NIL")
            else:
                self.expression(stmt.value)
            self.emit(f"DEFINE {stmt.name}")
        elif isinstance(stmt, sable.ExprStmt):
            if self.is_print(stmt.expr):
                self.print_call(stmt.expr, want_value=False)
            else:
                self.expression(stmt.expr)
                self.emit("POP")
        elif isinstance(stmt, sable.Block):
            for child in stmt.statements:
                self.statement(child)
        elif isinstance(stmt, sable.If):
            otherwise = self.label("else")
            end = self.label("end")
            self.expression(stmt.cond)
            self.emit(f"JUMP_IF_FALSE {otherwise}")
            self.statement(stmt.then_branch)
            self.emit(f"JUMP {end}")
            self.emit(f"LABEL {otherwise}")
            if stmt.else_branch is not None:
                self.statement(stmt.else_branch)
            self.emit(f"LABEL {end}")
        elif isinstance(stmt, sable.While):
            start = self.label("start")
            end = self.label("end")
            self.emit(f"LABEL {start}")
            self.expression(stmt.cond)
            self.emit(f"JUMP_IF_FALSE {end}")
            self.statement(stmt.body)
            self.emit(f"JUMP {start}")
            self.emit(f"LABEL {end}")
        else:
            raise NativeError(
                f"the native core milestone does not support {type(stmt).__name__} yet")

    def is_print(self, expr):
        return (isinstance(expr, sable.Call) and isinstance(expr.callee, sable.Var)
                and expr.callee.name == "print")

    def print_call(self, expr, want_value):
        for arg in expr.args:
            self.expression(arg)
        self.emit(f"PRINT {len(expr.args)}")
        if want_value:
            self.emit("PUSH_NIL")

    def expression(self, expr):
        if isinstance(expr, sable.Literal):
            value = expr.value
            if value is None:
                self.emit("PUSH_NIL")
            elif isinstance(value, bool):
                self.emit("PUSH_TRUE" if value else "PUSH_FALSE")
            elif isinstance(value, float):
                self.emit(f"PUSH_NUM {repr(value)}")
            elif isinstance(value, str):
                self.emit("PUSH_STR " + sasm_string(value))
            else:
                raise NativeError("unsupported literal")
        elif isinstance(expr, sable.Var):
            self.emit(f"LOAD {expr.name}")
        elif isinstance(expr, sable.Binary):
            self.expression(expr.left)
            self.expression(expr.right)
            ops = {
                "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
                "==": "EQ", "!=": "NE", "<": "LT", "<=": "LE",
                ">": "GT", ">=": "GE",
            }
            if expr.op not in ops:
                raise NativeError(f"unsupported operator {expr.op}")
            self.emit(ops[expr.op])
        elif isinstance(expr, sable.Unary):
            self.expression(expr.operand)
            self.emit("NOT" if expr.op == "not" else "NEG")
        elif isinstance(expr, sable.Assign):
            if not isinstance(expr.target, sable.Var):
                raise NativeError("native core milestone only supports variable assignment")
            if expr.op == "=":
                self.expression(expr.value)
                self.emit(f"STORE {expr.target.name}")
            else:
                self.emit(f"LOAD {expr.target.name}")
                self.expression(expr.value)
                ops = {"+=": "ADD", "-=": "SUB", "*=": "MUL", "/=": "DIV"}
                if expr.op not in ops:
                    raise NativeError(f"unsupported assignment {expr.op}")
                self.emit(ops[expr.op])
                self.emit(f"STORE {expr.target.name}")
        elif isinstance(expr, sable.Logical):
            if expr.op == "and":
                otherwise = self.label("false")
                end = self.label("end")
                self.expression(expr.left)
                self.emit(f"JUMP_IF_FALSE {otherwise}")
                self.expression(expr.right)
                self.emit(f"JUMP {end}")
                self.emit(f"LABEL {otherwise}")
                self.emit("PUSH_FALSE")
                self.emit(f"LABEL {end}")
            else:
                truthy = self.label("true")
                end = self.label("end")
                self.expression(expr.left)
                self.emit(f"JUMP_IF_TRUE {truthy}")
                self.expression(expr.right)
                self.emit(f"JUMP {end}")
                self.emit(f"LABEL {truthy}")
                self.emit("PUSH_TRUE")
                self.emit(f"LABEL {end}")
        elif isinstance(expr, sable.Call):
            if self.is_print(expr):
                self.print_call(expr, want_value=True)
            else:
                raise NativeError("native core milestone only supports print() calls")
        else:
            raise NativeError(
                f"the native core milestone does not support {type(expr).__name__} yet")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    try:
        with open(args.source, "r", encoding="utf-8") as handle:
            source = handle.read()
        program = sable.parse(source)
        sable.Checker().check(program)
        code = Compiler(program).compile()
    except (OSError, sable.SableError, NativeError) as error:
        print(f"sablec-native: {error}", file=sys.stderr)
        return 1
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(code + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
