#!/usr/bin/env python3
"""Sable: a small scripting language implemented as a tree-walking interpreter."""

import sys
import math
import bisect
from dataclasses import dataclass
from typing import Any, List, Optional

VERSION = "0.1.0"

sys.setrecursionlimit(10000)


class SableError(Exception):
    kind = "Error"

    def __init__(self, message, line=1, col=1):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col


class SableSyntaxError(SableError):
    kind = "SyntaxError"


class SableRuntimeError(SableError):
    kind = "RuntimeError"


KEYWORDS = {
    "let", "fn", "if", "else", "while", "for", "in", "return",
    "break", "continue", "true", "false", "nil", "and", "or", "not",
}


@dataclass
class Token:
    type: str
    value: Any
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, {self.line}:{self.col})"


class Lexer:
    def __init__(self, source):
        self.src = source
        self.pos = 0
        self.tokens = []
        self.line_starts = [0]
        for i, ch in enumerate(source):
            if ch == "\n":
                self.line_starts.append(i + 1)

    def position(self, offset):
        line = bisect.bisect_right(self.line_starts, offset)
        col = offset - self.line_starts[line - 1] + 1
        return line, col

    def error(self, offset, message):
        line, col = self.position(offset)
        raise SableSyntaxError(message, line, col)

    def add(self, type, value, start):
        line, col = self.position(start)
        self.tokens.append(Token(type, value, line, col))

    def scan(self):
        while self.pos < len(self.src):
            c = self.src[self.pos]
            if c in " \t\r\n":
                self.pos += 1
                continue
            if c == "/" and self.pos + 1 < len(self.src) and self.src[self.pos + 1] == "/":
                self.pos += 2
                while self.pos < len(self.src) and self.src[self.pos] != "\n":
                    self.pos += 1
                continue
            if c == "/" and self.pos + 1 < len(self.src) and self.src[self.pos + 1] == "*":
                start = self.pos
                self.pos += 2
                closed = False
                while self.pos + 1 < len(self.src):
                    if self.src[self.pos] == "*" and self.src[self.pos + 1] == "/":
                        self.pos += 2
                        closed = True
                        break
                    self.pos += 1
                if not closed:
                    self.error(start, "unterminated block comment")
                continue
            if c.isdigit():
                self.number()
                continue
            if c == '"':
                self.string()
                continue
            if c.isalpha() or c == "_":
                self.identifier()
                continue
            self.operator()
        line, col = self.position(len(self.src))
        self.tokens.append(Token("EOF", None, line, col))
        return self.tokens

    def number(self):
        start = self.pos
        while self.pos < len(self.src) and self.src[self.pos].isdigit():
            self.pos += 1
        if (self.pos + 1 < len(self.src) and self.src[self.pos] == "."
                and self.src[self.pos + 1].isdigit()):
            self.pos += 1
            while self.pos < len(self.src) and self.src[self.pos].isdigit():
                self.pos += 1
        if self.pos < len(self.src) and self.src[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.src) and self.src[self.pos] in "+-":
                self.pos += 1
            if self.pos < len(self.src) and self.src[self.pos].isdigit():
                while self.pos < len(self.src) and self.src[self.pos].isdigit():
                    self.pos += 1
            else:
                self.error(start, "malformed number")
        text = self.src[start:self.pos]
        try:
            value = float(text)
        except ValueError:
            self.error(start, f"malformed number {text!r}")
        self.add("NUMBER", value, start)

    def string(self):
        start = self.pos
        self.pos += 1
        out = []
        escapes = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}
        while self.pos < len(self.src):
            c = self.src[self.pos]
            if c == '"':
                self.pos += 1
                self.add("STRING", "".join(out), start)
                return
            if c == "\\":
                self.pos += 1
                if self.pos >= len(self.src):
                    self.error(start, "unterminated string")
                esc = self.src[self.pos]
                if esc not in escapes:
                    self.error(self.pos, f"unknown escape sequence \\{esc}")
                out.append(escapes[esc])
                self.pos += 1
                continue
            out.append(c)
            self.pos += 1
        self.error(start, "unterminated string")

    def identifier(self):
        start = self.pos
        while (self.pos < len(self.src)
               and (self.src[self.pos].isalnum() or self.src[self.pos] == "_")):
            self.pos += 1
        text = self.src[start:self.pos]
        if text in KEYWORDS:
            self.add(text, text, start)
        else:
            self.add("IDENT", text, start)

    def operator(self):
        start = self.pos
        two = self.src[self.pos:self.pos + 2]
        if two in ("==", "!=", "<=", ">=", "+=", "-=", "*=", "/="):
            self.pos += 2
            self.add(two, two, start)
            return
        c = self.src[self.pos]
        if c in "+-*/%=<>(){}[],:;":
            self.pos += 1
            self.add(c, c, start)
            return
        self.error(start, f"unexpected character {c!r}")


@dataclass
class Program:
    statements: List[Any]


@dataclass
class Let:
    line: int
    name: str
    value: Any


@dataclass
class FnDecl:
    line: int
    name: str
    params: List[str]
    body: Any


@dataclass
class If:
    line: int
    cond: Any
    then_branch: Any
    else_branch: Any


@dataclass
class While:
    line: int
    cond: Any
    body: Any


@dataclass
class For:
    line: int
    var: str
    iterable: Any
    body: Any


@dataclass
class Return:
    line: int
    value: Any


@dataclass
class Break:
    line: int


@dataclass
class Continue:
    line: int


@dataclass
class Block:
    line: int
    statements: List[Any]


@dataclass
class ExprStmt:
    line: int
    expr: Any


@dataclass
class Assign:
    line: int
    target: Any
    op: str
    value: Any


@dataclass
class Logical:
    line: int
    op: str
    left: Any
    right: Any


@dataclass
class Binary:
    line: int
    op: str
    left: Any
    right: Any


@dataclass
class Unary:
    line: int
    op: str
    operand: Any


@dataclass
class Call:
    line: int
    callee: Any
    args: List[Any]


@dataclass
class Index:
    line: int
    obj: Any
    index: Any


@dataclass
class Var:
    line: int
    name: str


@dataclass
class Literal:
    line: int
    value: Any


@dataclass
class ListLit:
    line: int
    elements: List[Any]


@dataclass
class MapLit:
    line: int
    pairs: List[Any]


@dataclass
class FnExpr:
    line: int
    params: List[str]
    body: Any


class Parser:
    def __init__(self, tokens, source):
        self.tokens = tokens
        self.source = source
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def peek(self, n=1):
        index = min(self.pos + n, len(self.tokens) - 1)
        return self.tokens[index]

    def check(self, type):
        return self.current().type == type

    def advance(self):
        tok = self.current()
        self.pos += 1
        return tok

    def match(self, *types):
        if self.current().type in types:
            return self.advance()
        return None

    def consume(self, type, message):
        if self.check(type):
            return self.advance()
        tok = self.current()
        raise SableSyntaxError(message, tok.line, tok.col)

    def error(self, message, tok=None):
        tok = tok or self.current()
        raise SableSyntaxError(message, tok.line, tok.col)

    def parse(self):
        statements = []
        while not self.check("EOF"):
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
        return Program(statements)

    def statement(self):
        if self.match(";"):
            return None
        if self.check("let"):
            return self.let_statement()
        if (self.check("fn") and self.peek().type == "IDENT"
                and self.peek(2).type == "("):
            return self.fn_declaration()
        if self.check("if"):
            return self.if_statement()
        if self.check("while"):
            return self.while_statement()
        if self.check("for"):
            return self.for_statement()
        if self.check("return"):
            return self.return_statement()
        if self.check("break"):
            tok = self.advance()
            self.consume(";", "expected ';' after 'break'")
            return Break(tok.line)
        if self.check("continue"):
            tok = self.advance()
            self.consume(";", "expected ';' after 'continue'")
            return Continue(tok.line)
        if self.check("{"):
            return self.block()
        expr = self.expression()
        self.consume(";", "expected ';' after expression")
        return ExprStmt(expr.line, expr)

    def let_statement(self):
        tok = self.advance()
        name = self.consume("IDENT", "expected a variable name after 'let'")
        value = None
        if self.match("="):
            value = self.expression()
        self.consume(";", "expected ';' after let")
        return Let(tok.line, name.value, value)

    def fn_declaration(self):
        tok = self.advance()
        name = self.consume("IDENT", "expected a function name")
        params = self.parameters()
        body = self.block()
        return FnDecl(tok.line, name.value, params, body)

    def parameters(self):
        self.consume("(", "expected '(' before parameters")
        params = []
        if not self.check(")"):
            while True:
                p = self.consume("IDENT", "expected a parameter name")
                params.append(p.value)
                if not self.match(","):
                    break
        self.consume(")", "expected ')' after parameters")
        return params

    def if_statement(self):
        tok = self.advance()
        cond = self.expression()
        then_branch = self.block()
        else_branch = None
        if self.match("else"):
            if self.check("if"):
                else_branch = self.if_statement()
            else:
                else_branch = self.block()
        return If(tok.line, cond, then_branch, else_branch)

    def while_statement(self):
        tok = self.advance()
        cond = self.expression()
        body = self.block()
        return While(tok.line, cond, body)

    def for_statement(self):
        tok = self.advance()
        var = self.consume("IDENT", "expected a loop variable")
        self.consume("in", "expected 'in' after the loop variable")
        iterable = self.expression()
        body = self.block()
        return For(tok.line, var.value, iterable, body)

    def return_statement(self):
        tok = self.advance()
        value = None
        if not self.check(";"):
            value = self.expression()
        self.consume(";", "expected ';' after return")
        return Return(tok.line, value)

    def block(self):
        tok = self.consume("{", "expected '{'")
        statements = []
        while not self.check("}") and not self.check("EOF"):
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
        self.consume("}", "expected '}' after block")
        return Block(tok.line, statements)

    def expression(self):
        return self.assignment()

    def assignment(self):
        expr = self.or_expr()
        if self.match("=", "+=", "-=", "*=", "/="):
            op = self.tokens[self.pos - 1].type
            if not isinstance(expr, (Var, Index)):
                self.error("invalid assignment target")
            value = self.assignment()
            return Assign(expr.line, expr, op, value)
        return expr

    def or_expr(self):
        expr = self.and_expr()
        while self.match("or"):
            right = self.and_expr()
            expr = Logical(expr.line, "or", expr, right)
        return expr

    def and_expr(self):
        expr = self.equality()
        while self.match("and"):
            right = self.equality()
            expr = Logical(expr.line, "and", expr, right)
        return expr

    def equality(self):
        expr = self.comparison()
        while self.match("==", "!="):
            op = self.tokens[self.pos - 1].type
            right = self.comparison()
            expr = Binary(expr.line, op, expr, right)
        return expr

    def comparison(self):
        expr = self.term()
        while self.match("<", "<=", ">", ">="):
            op = self.tokens[self.pos - 1].type
            right = self.term()
            expr = Binary(expr.line, op, expr, right)
        return expr

    def term(self):
        expr = self.factor()
        while self.match("+", "-"):
            op = self.tokens[self.pos - 1].type
            right = self.factor()
            expr = Binary(expr.line, op, expr, right)
        return expr

    def factor(self):
        expr = self.unary()
        while self.match("*", "/", "%"):
            op = self.tokens[self.pos - 1].type
            right = self.unary()
            expr = Binary(expr.line, op, expr, right)
        return expr

    def unary(self):
        if self.match("not", "-"):
            op = self.tokens[self.pos - 1]
            operand = self.unary()
            return Unary(op.line, op.type, operand)
        return self.postfix()

    def postfix(self):
        expr = self.primary()
        while True:
            if self.match("("):
                args = self.arguments()
                expr = Call(expr.line, expr, args)
            elif self.match("["):
                index = self.expression()
                self.consume("]", "expected ']' after index")
                expr = Index(expr.line, expr, index)
            else:
                break
        return expr

    def arguments(self):
        args = []
        if not self.check(")"):
            while True:
                args.append(self.expression())
                if not self.match(","):
                    break
        self.consume(")", "expected ')' after arguments")
        return args

    def primary(self):
        tok = self.current()
        if self.match("NUMBER"):
            return Literal(tok.line, tok.value)
        if self.match("STRING"):
            return Literal(tok.line, tok.value)
        if self.match("true"):
            return Literal(tok.line, True)
        if self.match("false"):
            return Literal(tok.line, False)
        if self.match("nil"):
            return Literal(tok.line, None)
        if self.match("IDENT"):
            return Var(tok.line, tok.value)
        if self.match("("):
            expr = self.expression()
            self.consume(")", "expected ')' after expression")
            return expr
        if self.match("["):
            elements = []
            if not self.check("]"):
                while True:
                    elements.append(self.expression())
                    if not self.match(","):
                        break
            self.consume("]", "expected ']' after list")
            return ListLit(tok.line, elements)
        if self.match("{"):
            pairs = []
            if not self.check("}"):
                while True:
                    key = self.expression()
                    self.consume(":", "expected ':' between map key and value")
                    value = self.expression()
                    pairs.append((key, value))
                    if not self.match(","):
                        break
            self.consume("}", "expected '}' after map")
            return MapLit(tok.line, pairs)
        if self.match("fn"):
            params = self.parameters()
            body = self.block()
            return FnExpr(tok.line, params, body)
        self.error(f"unexpected token {tok.type!r}")


class ReturnSignal(Exception):
    def __init__(self, value, line):
        self.value = value
        self.line = line


class BreakSignal(Exception):
    def __init__(self, line):
        self.line = line


class ContinueSignal(Exception):
    def __init__(self, line):
        self.line = line


class Environment:
    def __init__(self, parent=None):
        self.values = {}
        self.parent = parent

    def define(self, name, value):
        self.values[name] = value

    def get(self, name, line):
        env = self
        while env is not None:
            if name in env.values:
                return env.values[name]
            env = env.parent
        raise SableRuntimeError(f"undefined variable '{name}'", line)

    def assign(self, name, value, line):
        env = self
        while env is not None:
            if name in env.values:
                env.values[name] = value
                return
            env = env.parent
        raise SableRuntimeError(f"cannot assign to undefined variable '{name}'", line)


class Function:
    def __init__(self, name, params, body, closure):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure

    def __repr__(self):
        return f"<fn {self.name or 'anonymous'}>"


class Builtin:
    def __init__(self, name, fn, min_args, max_args):
        self.name = name
        self.fn = fn
        self.min_args = min_args
        self.max_args = max_args

    def __repr__(self):
        return f"<builtin {self.name}>"


def is_number(value):
    return isinstance(value, float)


def truthy(value):
    return value is not None and value is not False


def format_number(n):
    if math.isnan(n):
        return "nan"
    if math.isinf(n):
        return "inf" if n > 0 else "-inf"
    if n.is_integer() and abs(n) < 1e16:
        return str(int(n))
    return format(n, ".15g")


def repr_value(value):
    if isinstance(value, str):
        text = value.replace("\\", "\\\\").replace('"', '\\"')
        text = text.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
        return '"' + text + '"'
    return to_display(value)


def to_display(value):
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return format_number(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(repr_value(v) for v in value) + "]"
    if isinstance(value, dict):
        parts = [repr_value(k) + ": " + repr_value(v) for k, v in value.items()]
        return "{" + ", ".join(parts) + "}"
    if isinstance(value, (Function, Builtin)):
        return repr(value)
    return str(value)


def sable_equal(a, b):
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, float) and isinstance(b, float):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(sable_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(sable_equal(a[k], b[k]) for k in a)
    return a is b


def apply_binary(op, left, right, line):
    if op == "+":
        if is_number(left) and is_number(right):
            return left + right
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        if isinstance(left, list) and isinstance(right, list):
            return left + right
        raise SableRuntimeError("cannot add these values", line)
    if op in ("-", "*", "/", "%"):
        if not (is_number(left) and is_number(right)):
            raise SableRuntimeError(f"operator '{op}' expects numbers", line)
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise SableRuntimeError("division by zero", line)
            return left / right
        if right == 0:
            raise SableRuntimeError("division by zero", line)
        return math.fmod(left, right)
    if op == "==":
        return sable_equal(left, right)
    if op == "!=":
        return not sable_equal(left, right)
    if op in ("<", "<=", ">", ">="):
        if not ((is_number(left) and is_number(right))
                or (isinstance(left, str) and isinstance(right, str))):
            raise SableRuntimeError(f"operator '{op}' cannot compare these values", line)
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        return left >= right
    raise SableRuntimeError(f"unknown operator '{op}'", line)


