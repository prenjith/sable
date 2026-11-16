#!/usr/bin/env python3
"""Sable: a small scripting language implemented as a tree-walking interpreter."""

import sys
import os
import math
import bisect
import functools
import threading
import time
from dataclasses import dataclass
from typing import Any, List, Optional

VERSION = "0.9.0"

sys.setrecursionlimit(10000)


class SableError(Exception):
    kind = "Error"

    def __init__(self, message, line=1, col=1):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.source = None
        self.filename = None


class SableSyntaxError(SableError):
    kind = "SyntaxError"


class SableRuntimeError(SableError):
    kind = "RuntimeError"


class SableThrown(Exception):
    def __init__(self, value, line):
        self.value = value
        self.line = line


KEYWORDS = {
    "let", "const", "fn", "if", "else", "while", "for", "in", "return",
    "break", "continue", "try", "catch", "throw", "match", "import",
    "class", "new", "this",
    "true", "false", "nil", "and", "or", "not",
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
        if two in ("==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "=>", "|>"):
            self.pos += 2
            self.add(two, two, start)
            return
        c = self.src[self.pos]
        if c in "+-*/%=<>(){}[],:;.":
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
    type_name: Any = None


@dataclass
class FnDecl:
    line: int
    name: str
    params: List[str]
    body: Any
    param_types: Any = None
    return_type: Any = None


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
class ClassDecl:
    line: int
    name: str
    methods: List[Any]


@dataclass
class New:
    line: int
    name: str
    args: List[Any]


@dataclass
class Import:
    line: int
    path: str


@dataclass
class Const:
    line: int
    name: str
    value: Any
    type_name: Any = None


@dataclass
class TryCatch:
    line: int
    try_block: Any
    error_name: str
    catch_block: Any


@dataclass
class Throw:
    line: int
    value: Any


@dataclass
class Match:
    line: int
    value: Any
    arms: List[Any]


@dataclass
class Pipe:
    line: int
    left: Any
    right: Any


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
    param_types: Any = None
    return_type: Any = None


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
        if self.check("const"):
            return self.const_statement()
        if self.check("try"):
            return self.try_statement()
        if self.check("throw"):
            return self.throw_statement()
        if self.check("match"):
            return self.match_statement()
        if self.check("import"):
            return self.import_statement()
        if self.check("class"):
            return self.class_statement()
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
        type_name = None
        if self.match(":"):
            type_name = self.type_name()
        value = None
        if self.match("="):
            value = self.expression()
        self.consume(";", "expected ';' after let")
        return Let(tok.line, name.value, value, type_name)

    def fn_declaration(self):
        tok = self.advance()
        name = self.consume("IDENT", "expected a function name")
        params, param_types = self.parameters()
        return_type = None
        if self.match(":"):
            return_type = self.type_name()
        body = self.block()
        return FnDecl(tok.line, name.value, params, body, param_types, return_type)

    def parameters(self):
        self.consume("(", "expected '(' before parameters")
        params = []
        param_types = []
        if not self.check(")"):
            while True:
                p = self.consume("IDENT", "expected a parameter name")
                params.append(p.value)
                if self.match(":"):
                    param_types.append(self.type_name())
                else:
                    param_types.append(None)
                if not self.match(","):
                    break
        self.consume(")", "expected ')' after parameters")
        return params, param_types

    def type_name(self):
        tok = self.consume("IDENT", "expected a type name")
        return tok.value

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

    def class_statement(self):
        tok = self.advance()
        name = self.consume("IDENT", "expected a class name")
        self.consume("{", "expected '{' after the class name")
        methods = []
        while not self.check("}") and not self.check("EOF"):
            if not self.check("fn"):
                self.error("expected a method declaration")
            methods.append(self.fn_declaration())
        self.consume("}", "expected '}' after the class body")
        return ClassDecl(tok.line, name.value, methods)

    def import_statement(self):
        tok = self.advance()
        path = self.consume("STRING", "expected a file path after 'import'")
        self.consume(";", "expected ';' after import")
        return Import(tok.line, path.value)

    def const_statement(self):
        tok = self.advance()
        name = self.consume("IDENT", "expected a name after 'const'")
        type_name = None
        if self.match(":"):
            type_name = self.type_name()
        self.consume("=", "const declarations need a value")
        value = self.expression()
        self.consume(";", "expected ';' after const")
        return Const(tok.line, name.value, value, type_name)

    def try_statement(self):
        tok = self.advance()
        try_block = self.block()
        self.consume("catch", "expected 'catch' after the try block")
        name = self.consume("IDENT", "expected an error name after 'catch'")
        catch_block = self.block()
        return TryCatch(tok.line, try_block, name.value, catch_block)

    def throw_statement(self):
        tok = self.advance()
        value = self.expression()
        self.consume(";", "expected ';' after throw")
        return Throw(tok.line, value)

    def match_statement(self):
        tok = self.advance()
        value = self.expression()
        self.consume("{", "expected '{' after the match value")
        arms = []
        while not self.check("}") and not self.check("EOF"):
            pattern = self.pattern()
            self.consume("=>", "expected '=>' after a match pattern")
            body = self.statement()
            if body is not None:
                arms.append((pattern, body))
        self.consume("}", "expected '}' after match arms")
        return Match(tok.line, value, arms)

    def pattern(self):
        tok = self.current()
        if self.match("NUMBER"):
            return ("literal", tok.value)
        if self.match("STRING"):
            return ("literal", tok.value)
        if self.match("true"):
            return ("literal", True)
        if self.match("false"):
            return ("literal", False)
        if self.match("nil"):
            return ("literal", None)
        if self.match("IDENT"):
            if tok.value == "_":
                return ("wild", None)
            return ("bind", tok.value)
        self.error("expected a match pattern")

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
        expr = self.pipe()
        if self.match("=", "+=", "-=", "*=", "/="):
            op = self.tokens[self.pos - 1].type
            if not isinstance(expr, (Var, Index)):
                self.error("invalid assignment target")
            value = self.assignment()
            return Assign(expr.line, expr, op, value)
        return expr

    def pipe(self):
        expr = self.or_expr()
        while self.match("|>"):
            right = self.or_expr()
            expr = Pipe(expr.line, expr, right)
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
            elif self.match("."):
                name = self.consume("IDENT", "expected a property name after '.'")
                expr = Index(expr.line, expr, Literal(name.line, name.value))
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
        if self.match("new"):
            name = self.consume("IDENT", "expected a class name after 'new'")
            self.consume("(", "expected '(' after the class name")
            args = self.arguments()
            return New(tok.line, name.value, args)
        if self.match("this"):
            return Var(tok.line, "this")
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
            params, param_types = self.parameters()
            return_type = None
            if self.match(":"):
                return_type = self.type_name()
            body = self.block()
            return FnExpr(tok.line, params, body, param_types, return_type)
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
        self.constants = set()
        self.parent = parent

    def define(self, name, value, constant=False):
        self.values[name] = value
        if constant:
            self.constants.add(name)

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
                if name in env.constants:
                    raise SableRuntimeError(f"cannot assign to constant '{name}'", line)
                env.values[name] = value
                return
            env = env.parent
        raise SableRuntimeError(f"cannot assign to undefined variable '{name}'", line)


class Function:
    def __init__(self, name, params, body, closure, param_types=None, return_type=None):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure
        self.param_types = param_types
        self.return_type = return_type

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


class SableClass:
    def __init__(self, name, methods):
        self.name = name
        self.methods = methods

    def __repr__(self):
        return f"<class {self.name}>"


class SableObject:
    def __init__(self, klass):
        self.klass = klass
        self.fields = SableMap()

    def __repr__(self):
        return f"<{self.klass.name} object>"


class Task:
    def __init__(self, thread, box):
        self.thread = thread
        self.box = box

    def __repr__(self):
        return "<task>"


class BoundMethod:
    def __init__(self, function, receiver):
        self.function = function
        self.receiver = receiver

    def __repr__(self):
        return f"<bound {self.function.name or 'method'}>"


class SableMap:
    def __init__(self):
        self.entries = {}

    @staticmethod
    def normalize(key):
        if key is None:
            return ("nil",)
        if isinstance(key, bool):
            return ("bool", key)
        if isinstance(key, float):
            return ("num", key)
        if isinstance(key, str):
            return ("str", key)
        raise SableRuntimeError("map keys must be strings, numbers, booleans, or nil")

    def set(self, key, value):
        self.entries[self.normalize(key)] = (key, value)

    def get(self, key):
        entry = self.entries.get(self.normalize(key))
        return entry[1] if entry is not None else None

    def has(self, key):
        return self.normalize(key) in self.entries

    def keys(self):
        return [entry[0] for entry in self.entries.values()]

    def items(self):
        return [(entry[0], entry[1]) for entry in self.entries.values()]

    def __len__(self):
        return len(self.entries)

    def __eq__(self, other):
        if not isinstance(other, SableMap):
            return False
        if len(self) != len(other):
            return False
        for key, value in self.items():
            if not other.has(key) or not sable_equal(value, other.get(key)):
                return False
        return True

    def __repr__(self):
        return f"SableMap({self.items()!r})"


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
    if isinstance(value, SableMap):
        parts = [repr_value(k) + ": " + repr_value(v) for k, v in value.items()]
        return "{" + ", ".join(parts) + "}"
    if isinstance(value, (Function, Builtin, SableClass, SableObject, BoundMethod, Task)):
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
    if isinstance(a, SableMap) and isinstance(b, SableMap):
        return a == b
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


class SableTypeError(SableError):
    kind = "TypeError"


class FunctionType:
    def __init__(self, param_types, return_type):
        self.param_types = param_types
        self.return_type = return_type


class Checker:
    def __init__(self):
        self.scopes = [{}]
        self.function_scopes = [{}]
        self.return_types = []

    def check(self, program):
        for stmt in program.statements:
            self.check_stmt(stmt)

    def push(self):
        self.scopes.append({})
        self.function_scopes.append({})

    def pop(self):
        self.scopes.pop()
        self.function_scopes.pop()

    def declare(self, name, type_name):
        self.scopes[-1][name] = type_name

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return "any"

    def declare_function(self, name, signature):
        self.function_scopes[-1][name] = signature
        self.scopes[-1][name] = "function"

    def lookup_function(self, name):
        for scope in reversed(self.function_scopes):
            if name in scope:
                return scope[name]
        return None

    def compatible(self, expected, actual):
        if expected == "any" or actual == "any":
            return True
        return expected == actual

    def expect(self, expected, actual, line, context):
        if not self.compatible(expected, actual):
            raise SableTypeError(f"{context}: expected {expected}, got {actual}", line)

    def check_stmt(self, stmt):
        getattr(self, "check_" + type(stmt).__name__)(stmt)

    def check_Let(self, stmt):
        actual = "nil" if stmt.value is None else self.infer(stmt.value)
        declared = stmt.type_name or "any"
        if stmt.type_name:
            self.expect(declared, actual, stmt.line, f"cannot initialize '{stmt.name}'")
        self.declare(stmt.name, declared)

    def check_Const(self, stmt):
        actual = self.infer(stmt.value)
        declared = stmt.type_name or "any"
        if stmt.type_name:
            self.expect(declared, actual, stmt.line, f"cannot initialize '{stmt.name}'")
        self.declare(stmt.name, declared)

    def check_FnDecl(self, stmt):
        param_types = [t or "any" for t in (stmt.param_types or [None] * len(stmt.params))]
        return_type = stmt.return_type or "any"
        self.declare_function(stmt.name, FunctionType(param_types, return_type))
        self.push()
        for name, type_name in zip(stmt.params, param_types):
            self.declare(name, type_name)
        self.return_types.append(return_type)
        self.check_stmt(stmt.body)
        self.return_types.pop()
        self.pop()

    def check_If(self, stmt):
        self.infer(stmt.cond)
        self.push()
        self.check_stmt(stmt.then_branch)
        self.pop()
        if stmt.else_branch is not None:
            self.push()
            self.check_stmt(stmt.else_branch)
            self.pop()

    def check_While(self, stmt):
        self.infer(stmt.cond)
        self.push()
        self.check_stmt(stmt.body)
        self.pop()

    def check_For(self, stmt):
        self.infer(stmt.iterable)
        self.push()
        self.declare(stmt.var, "any")
        self.check_stmt(stmt.body)
        self.pop()

    def check_Return(self, stmt):
        actual = "nil" if stmt.value is None else self.infer(stmt.value)
        expected = self.return_types[-1] if self.return_types else "any"
        if expected != "any":
            self.expect(expected, actual, stmt.line, "return value")

    def check_Break(self, stmt):
        pass

    def check_Continue(self, stmt):
        pass

    def check_TryCatch(self, stmt):
        self.push()
        self.check_stmt(stmt.try_block)
        self.pop()
        self.push()
        self.declare(stmt.error_name, "any")
        self.check_stmt(stmt.catch_block)
        self.pop()

    def check_Throw(self, stmt):
        self.infer(stmt.value)

    def check_Match(self, stmt):
        self.infer(stmt.value)
        for pattern, body in stmt.arms:
            self.push()
            kind, data = pattern
            if kind == "bind":
                self.declare(data, "any")
            self.check_stmt(body)
            self.pop()

    def check_Block(self, stmt):
        self.push()
        for child in stmt.statements:
            self.check_stmt(child)
        self.pop()

    def check_ExprStmt(self, stmt):
        self.infer(stmt.expr)

    def check_Import(self, stmt):
        pass

    def check_ClassDecl(self, stmt):
        for method in stmt.methods:
            param_types = [t or "any" for t in (method.param_types or [None] * len(method.params))]
            return_type = method.return_type or "any"
            self.push()
            self.declare("this", "any")
            for name, type_name in zip(method.params, param_types):
                self.declare(name, type_name)
            self.return_types.append(return_type)
            self.check_stmt(method.body)
            self.return_types.pop()
            self.pop()

    def infer(self, expr):
        return getattr(self, "infer_" + type(expr).__name__)(expr)

    def infer_Literal(self, expr):
        value = expr.value
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        return "any"

    def infer_Var(self, expr):
        return self.lookup(expr.name)

    def infer_ListLit(self, expr):
        for element in expr.elements:
            self.infer(element)
        return "list"

    def infer_MapLit(self, expr):
        for key, value in expr.pairs:
            self.infer(key)
            self.infer(value)
        return "map"

    def infer_FnExpr(self, expr):
        param_types = [t or "any" for t in (expr.param_types or [None] * len(expr.params))]
        return_type = expr.return_type or "any"
        self.push()
        for name, type_name in zip(expr.params, param_types):
            self.declare(name, type_name)
        self.return_types.append(return_type)
        self.check_stmt(expr.body)
        self.return_types.pop()
        self.pop()
        return "function"

    def infer_Unary(self, expr):
        operand = self.infer(expr.operand)
        if expr.op == "not":
            return "bool"
        self.expect("number", operand, expr.line, "unary '-'")
        return "number"

    def infer_Binary(self, expr):
        left = self.infer(expr.left)
        right = self.infer(expr.right)
        op = expr.op
        if op == "+":
            if left == "any" or right == "any":
                return "any"
            if left == "number" and right == "number":
                return "number"
            if left == "string" and right == "string":
                return "string"
            if left == "list" and right == "list":
                return "list"
            raise SableTypeError(f"cannot add {left} and {right}", expr.line)
        if op in ("-", "*", "/", "%"):
            self.expect("number", left, expr.line, f"operator '{op}'")
            self.expect("number", right, expr.line, f"operator '{op}'")
            return "number"
        if op in ("<", "<=", ">", ">="):
            if left == "any" or right == "any":
                return "bool"
            if left == right and left in ("number", "string"):
                return "bool"
            raise SableTypeError(f"cannot compare {left} and {right}", expr.line)
        if op in ("==", "!="):
            return "bool"
        return "any"

    def infer_Logical(self, expr):
        self.infer(expr.left)
        self.infer(expr.right)
        return "any"

    def infer_Assign(self, expr):
        actual = self.infer(expr.value)
        target = expr.target
        if isinstance(target, Var):
            expected = self.lookup(target.name)
            if expr.op == "=" and expected != "any":
                self.expect(expected, actual, expr.line, f"cannot assign to '{target.name}'")
            return expected if expected != "any" else actual
        if isinstance(target, Index):
            self.infer(target.obj)
            self.infer(target.index)
            return actual
        return "any"

    def infer_Call(self, expr):
        if isinstance(expr.callee, Var):
            signature = self.lookup_function(expr.callee.name)
            if signature is not None:
                if len(expr.args) != len(signature.param_types):
                    raise SableTypeError(
                        f"{expr.callee.name}() expects {len(signature.param_types)} argument(s), got {len(expr.args)}",
                        expr.line)
                for argument, expected in zip(expr.args, signature.param_types):
                    self.expect(expected, self.infer(argument), expr.line,
                                f"argument to {expr.callee.name}()")
                return signature.return_type
        self.infer(expr.callee)
        for argument in expr.args:
            self.infer(argument)
        return "any"

    def infer_New(self, expr):
        for argument in expr.args:
            self.infer(argument)
        return "object"

    def infer_Index(self, expr):
        obj = self.infer(expr.obj)
        self.infer(expr.index)
        if obj in ("list", "string", "map", "object", "any"):
            return "any"
        raise SableTypeError(f"cannot index a {obj}", expr.line)

    def infer_Pipe(self, expr):
        left = self.infer(expr.left)
        if isinstance(expr.right, Call) and isinstance(expr.right.callee, Var):
            signature = self.lookup_function(expr.right.callee.name)
            if signature is not None:
                if 1 + len(expr.right.args) != len(signature.param_types):
                    raise SableTypeError(
                        f"{expr.right.callee.name}() expects {len(signature.param_types)} argument(s), got {1 + len(expr.right.args)}",
                        expr.line)
                self.expect(signature.param_types[0], left, expr.line,
                            f"argument to {expr.right.callee.name}()")
                for argument, expected in zip(expr.right.args, signature.param_types[1:]):
                    self.expect(expected, self.infer(argument), expr.line,
                                f"argument to {expr.right.callee.name}()")
                return signature.return_type
        self.infer(expr.right)
        return "any"


class Verifier:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.loop_depth = 0
        self.function_depth = 0

    def verify(self, program):
        for stmt in program.statements:
            self.check_stmt(stmt)
        return self.errors, self.warnings

    def error(self, line, message):
        self.errors.append((line, message))

    def warning(self, line, message):
        self.warnings.append((line, message))

    def check_stmt(self, stmt):
        getattr(self, "check_" + type(stmt).__name__)(stmt)

    def check_Block(self, stmt):
        terminated = False
        for child in stmt.statements:
            if terminated:
                self.warning(child.line, "unreachable code")
            self.check_stmt(child)
            if isinstance(child, (Return, Break, Continue, Throw)):
                terminated = True

    def check_Let(self, stmt):
        if stmt.value is not None:
            self.check_expr(stmt.value)

    def check_Const(self, stmt):
        self.check_expr(stmt.value)

    def check_If(self, stmt):
        self.check_expr(stmt.cond)
        self.check_stmt(stmt.then_branch)
        if stmt.else_branch is not None:
            self.check_stmt(stmt.else_branch)

    def check_While(self, stmt):
        self.check_expr(stmt.cond)
        self.loop_depth += 1
        self.check_stmt(stmt.body)
        self.loop_depth -= 1

    def check_For(self, stmt):
        self.check_expr(stmt.iterable)
        self.loop_depth += 1
        self.check_stmt(stmt.body)
        self.loop_depth -= 1

    def check_Return(self, stmt):
        if self.function_depth == 0:
            self.error(stmt.line, "'return' outside a function")
        if stmt.value is not None:
            self.check_expr(stmt.value)

    def check_Break(self, stmt):
        if self.loop_depth == 0:
            self.error(stmt.line, "'break' outside a loop")

    def check_Continue(self, stmt):
        if self.loop_depth == 0:
            self.error(stmt.line, "'continue' outside a loop")

    def check_Throw(self, stmt):
        self.check_expr(stmt.value)

    def check_TryCatch(self, stmt):
        self.check_stmt(stmt.try_block)
        self.check_stmt(stmt.catch_block)

    def check_Match(self, stmt):
        self.check_expr(stmt.value)
        catch_all = False
        for pattern, body in stmt.arms:
            if catch_all:
                self.warning(body.line, "unreachable match arm")
            if pattern[0] in ("wild", "bind"):
                catch_all = True
            self.check_stmt(body)

    def check_FnDecl(self, stmt):
        saved_loops = self.loop_depth
        self.loop_depth = 0
        self.function_depth += 1
        self.check_stmt(stmt.body)
        self.function_depth -= 1
        self.loop_depth = saved_loops

    def check_ClassDecl(self, stmt):
        for method in stmt.methods:
            saved_loops = self.loop_depth
            self.loop_depth = 0
            self.function_depth += 1
            self.check_stmt(method.body)
            self.function_depth -= 1
            self.loop_depth = saved_loops

    def check_ExprStmt(self, stmt):
        self.check_expr(stmt.expr)

    def check_Import(self, stmt):
        pass

    def check_expr(self, expr):
        getattr(self, "expr_" + type(expr).__name__)(expr)

    def expr_Literal(self, expr):
        pass

    def expr_Var(self, expr):
        pass

    def expr_ListLit(self, expr):
        for element in expr.elements:
            self.check_expr(element)

    def expr_MapLit(self, expr):
        seen = set()
        for key, value in expr.pairs:
            marker = None
            if key.value is None:
                marker = ("nil",)
            elif isinstance(key.value, bool):
                marker = ("bool", key.value)
            elif isinstance(key.value, float):
                marker = ("num", key.value)
            elif isinstance(key.value, str):
                marker = ("str", key.value)
            if marker is not None:
                if marker in seen:
                    self.warning(key.line, "duplicate map key")
                seen.add(marker)
            self.check_expr(key)
            self.check_expr(value)

    def expr_FnExpr(self, expr):
        saved_loops = self.loop_depth
        self.loop_depth = 0
        self.function_depth += 1
        self.check_stmt(expr.body)
        self.function_depth -= 1
        self.loop_depth = saved_loops

    def expr_Unary(self, expr):
        self.check_expr(expr.operand)

    def expr_Binary(self, expr):
        self.check_expr(expr.left)
        self.check_expr(expr.right)

    def expr_Logical(self, expr):
        self.check_expr(expr.left)
        self.check_expr(expr.right)

    def expr_Assign(self, expr):
        if isinstance(expr.target, Index):
            self.check_expr(expr.target.obj)
            self.check_expr(expr.target.index)
        self.check_expr(expr.value)

    def expr_Call(self, expr):
        self.check_expr(expr.callee)
        for argument in expr.args:
            self.check_expr(argument)

    def expr_Index(self, expr):
        self.check_expr(expr.obj)
        self.check_expr(expr.index)

    def expr_Pipe(self, expr):
        self.check_expr(expr.left)
        self.check_expr(expr.right)

    def expr_New(self, expr):
        for argument in expr.args:
            self.check_expr(argument)


class Interpreter:
    def __init__(self, base_dir="."):
        self.globals = Environment()
        self.base_dir = base_dir
        self.loaded_modules = set()
        self.local = threading.local()
        self.install_builtins()

    def run(self, program):
        result = None
        try:
            for stmt in program.statements:
                result = self.execute(stmt, self.globals)
        except ReturnSignal as signal:
            raise SableRuntimeError("'return' outside a function", signal.line)
        except BreakSignal as signal:
            raise SableRuntimeError("'break' outside a loop", signal.line)
        except ContinueSignal as signal:
            raise SableRuntimeError("'continue' outside a loop", signal.line)
        except SableThrown as thrown:
            raise SableRuntimeError("uncaught: " + to_display(thrown.value), thrown.line)
        return result

    def execute(self, stmt, env):
        method = getattr(self, "exec_" + type(stmt).__name__)
        return method(stmt, env)

    def evaluate(self, expr, env):
        method = getattr(self, "eval_" + type(expr).__name__)
        return method(expr, env)

    def exec_Block(self, stmt, env):
        block_env = Environment(env)
        result = None
        for child in stmt.statements:
            result = self.execute(child, block_env)
        return result

    def exec_Let(self, stmt, env):
        value = None if stmt.value is None else self.evaluate(stmt.value, env)
        env.define(stmt.name, value)
        return None

    def exec_ClassDecl(self, stmt, env):
        methods = {}
        for method in stmt.methods:
            methods[method.name] = Function(method.name, method.params, method.body, env,
                                            method.param_types, method.return_type)
        env.define(stmt.name, SableClass(stmt.name, methods))
        return None

    def exec_Import(self, stmt, env):
        path = os.path.abspath(os.path.join(self.base_dir, stmt.path))
        if path in self.loaded_modules:
            return None
        self.loaded_modules.add(path)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                source = handle.read()
        except OSError as error:
            raise SableRuntimeError(f"cannot import {stmt.path!r}: {error}", stmt.line)
        try:
            program = parse(source)
            Checker().check(program)
            previous = self.base_dir
            self.base_dir = os.path.dirname(path)
            try:
                for child in program.statements:
                    self.execute(child, self.globals)
            finally:
                self.base_dir = previous
        except SableError as error:
            error.source = source
            error.filename = path
            raise
        return None

    def exec_Const(self, stmt, env):
        value = self.evaluate(stmt.value, env)
        env.define(stmt.name, value, constant=True)
        return None

    def exec_TryCatch(self, stmt, env):
        try:
            return self.execute(stmt.try_block, env)
        except SableThrown as thrown:
            error_env = Environment(env)
            error_env.define(stmt.error_name, thrown.value)
            return self.execute(stmt.catch_block, error_env)
        except SableRuntimeError as error:
            error_env = Environment(env)
            info = SableMap()
            info.set("message", error.message)
            info.set("line", float(error.line))
            error_env.define(stmt.error_name, info)
            return self.execute(stmt.catch_block, error_env)

    def exec_Throw(self, stmt, env):
        value = self.evaluate(stmt.value, env)
        raise SableThrown(value, stmt.line)

    def exec_Match(self, stmt, env):
        value = self.evaluate(stmt.value, env)
        for pattern, body in stmt.arms:
            kind, data = pattern
            arm_env = Environment(env)
            if kind == "wild":
                matched = True
            elif kind == "bind":
                arm_env.define(data, value)
                matched = True
            else:
                matched = sable_equal(value, data)
            if matched:
                return self.execute(body, arm_env)
        return None

    def exec_FnDecl(self, stmt, env):
        env.define(stmt.name, Function(stmt.name, stmt.params, stmt.body, env,
                                        stmt.param_types, stmt.return_type))
        return None

    def exec_If(self, stmt, env):
        if truthy(self.evaluate(stmt.cond, env)):
            return self.execute(stmt.then_branch, env)
        if stmt.else_branch is not None:
            return self.execute(stmt.else_branch, env)
        return None

    def exec_While(self, stmt, env):
        while truthy(self.evaluate(stmt.cond, env)):
            try:
                self.execute(stmt.body, env)
            except ContinueSignal:
                continue
            except BreakSignal:
                break
        return None

    def exec_For(self, stmt, env):
        iterable = self.evaluate(stmt.iterable, env)
        for item in self.iterable_items(iterable, stmt.line):
            loop_env = Environment(env)
            loop_env.define(stmt.var, item)
            try:
                self.execute(stmt.body, loop_env)
            except ContinueSignal:
                continue
            except BreakSignal:
                break
        return None

    def exec_Return(self, stmt, env):
        value = None if stmt.value is None else self.evaluate(stmt.value, env)
        raise ReturnSignal(value, stmt.line)

    def exec_Break(self, stmt, env):
        raise BreakSignal(stmt.line)

    def exec_Continue(self, stmt, env):
        raise ContinueSignal(stmt.line)

    def exec_ExprStmt(self, stmt, env):
        return self.evaluate(stmt.expr, env)

    def eval_Literal(self, expr, env):
        return expr.value

    def eval_Var(self, expr, env):
        return env.get(expr.name, expr.line)

    def eval_Assign(self, expr, env):
        target = expr.target
        if isinstance(target, Var):
            if expr.op == "=":
                value = self.evaluate(expr.value, env)
            else:
                current = env.get(target.name, expr.line)
                value = apply_binary(expr.op[:-1], current,
                                     self.evaluate(expr.value, env), expr.line)
            env.assign(target.name, value, expr.line)
            return value
        if isinstance(target, Index):
            obj = self.evaluate(target.obj, env)
            index = self.evaluate(target.index, env)
            if expr.op == "=":
                value = self.evaluate(expr.value, env)
            else:
                current = self.get_index(obj, index, expr.line)
                value = apply_binary(expr.op[:-1], current,
                                     self.evaluate(expr.value, env), expr.line)
            self.set_index(obj, index, value, expr.line)
            return value
        raise SableRuntimeError("invalid assignment target", expr.line)

    def eval_Logical(self, expr, env):
        left = self.evaluate(expr.left, env)
        if expr.op == "or":
            if truthy(left):
                return left
            return self.evaluate(expr.right, env)
        if not truthy(left):
            return left
        return self.evaluate(expr.right, env)

    def eval_Pipe(self, expr, env):
        value = self.evaluate(expr.left, env)
        if isinstance(expr.right, Call):
            function = self.evaluate(expr.right.callee, env)
            args = [self.evaluate(arg, env) for arg in expr.right.args]
            return self.call_value(function, [value] + args, expr.line)
        function = self.evaluate(expr.right, env)
        return self.call_value(function, [value], expr.line)

    def eval_Binary(self, expr, env):
        left = self.evaluate(expr.left, env)
        right = self.evaluate(expr.right, env)
        return apply_binary(expr.op, left, right, expr.line)

    def eval_Unary(self, expr, env):
        value = self.evaluate(expr.operand, env)
        if expr.op == "not":
            return not truthy(value)
        if not is_number(value):
            raise SableRuntimeError("unary '-' expects a number", expr.line)
        return -value

    def eval_Call(self, expr, env):
        callee = self.evaluate(expr.callee, env)
        args = [self.evaluate(arg, env) for arg in expr.args]
        return self.call_value(callee, args, expr.line)

    def eval_Index(self, expr, env):
        obj = self.evaluate(expr.obj, env)
        index = self.evaluate(expr.index, env)
        return self.get_index(obj, index, expr.line)

    def eval_ListLit(self, expr, env):
        return [self.evaluate(item, env) for item in expr.elements]

    def eval_MapLit(self, expr, env):
        result = SableMap()
        for key_expr, value_expr in expr.pairs:
            key = self.evaluate(key_expr, env)
            result.set(key, self.evaluate(value_expr, env))
        return result

    def eval_New(self, expr, env):
        klass = env.get(expr.name, expr.line)
        if not isinstance(klass, SableClass):
            raise SableRuntimeError(f"'{expr.name}' is not a class", expr.line)
        obj = SableObject(klass)
        args = [self.evaluate(arg, env) for arg in expr.args]
        if "init" in klass.methods:
            self.call_function(klass.methods["init"], args, expr.line, obj)
        elif args:
            raise SableRuntimeError(f"{klass.name}() takes no arguments", expr.line)
        return obj

    def eval_FnExpr(self, expr, env):
        return Function(None, expr.params, expr.body, env,
                        expr.param_types, expr.return_type)

    def call_value(self, callee, args, line):
        if isinstance(callee, Builtin):
            if len(args) < callee.min_args or (callee.max_args is not None
                                               and len(args) > callee.max_args):
                raise SableRuntimeError(
                    f"{callee.name}() got {len(args)} argument(s)", line)
            return callee.fn(args, line)
        if isinstance(callee, Function):
            return self.call_function(callee, args, line)
        if isinstance(callee, BoundMethod):
            return self.call_function(callee.function, args, line, callee.receiver)
        raise SableRuntimeError("value is not callable", line)

    def call_function(self, function, args, line, receiver=None):
        if len(args) != len(function.params):
            name = function.name or "function"
            raise SableRuntimeError(
                f"{name}() expects {len(function.params)} argument(s), got {len(args)}",
                line)
        depth = getattr(self.local, "depth", 0) + 1
        self.local.depth = depth
        if depth > 1000:
            self.local.depth = depth - 1
            raise SableRuntimeError("stack overflow", line)
        call_env = Environment(function.closure)
        if receiver is not None:
            call_env.define("this", receiver)
        for name, value in zip(function.params, args):
            call_env.define(name, value)
        try:
            self.execute(function.body, call_env)
        except ReturnSignal as signal:
            return signal.value
        except BreakSignal as signal:
            raise SableRuntimeError("'break' outside a loop", signal.line)
        except ContinueSignal as signal:
            raise SableRuntimeError("'continue' outside a loop", signal.line)
        finally:
            self.local.depth = depth - 1
        return None

    def iterable_items(self, value, line):
        if isinstance(value, list):
            return list(value)
        if isinstance(value, str):
            return list(value)
        if isinstance(value, SableMap):
            return value.keys()
        raise SableRuntimeError("value is not iterable", line)

    def require_int(self, value, line, what):
        if not is_number(value) or not value.is_integer():
            raise SableRuntimeError(f"{what} must be an integer", line)
        return int(value)

    def get_index(self, obj, index, line):
        if isinstance(obj, list):
            i = self.require_int(index, line, "list index")
            if i < 0:
                i += len(obj)
            if i < 0 or i >= len(obj):
                raise SableRuntimeError("list index out of range", line)
            return obj[i]
        if isinstance(obj, str):
            i = self.require_int(index, line, "string index")
            if i < 0:
                i += len(obj)
            if i < 0 or i >= len(obj):
                raise SableRuntimeError("string index out of range", line)
            return obj[i]
        if isinstance(obj, SableMap):
            return obj.get(index)
        if isinstance(obj, SableObject):
            if not isinstance(index, str):
                raise SableRuntimeError("object fields must be strings", line)
            if obj.fields.has(index):
                return obj.fields.get(index)
            if index in obj.klass.methods:
                return BoundMethod(obj.klass.methods[index], obj)
            raise SableRuntimeError(f"{obj.klass.name} has no field '{index}'", line)
        raise SableRuntimeError("value is not indexable", line)

    def set_index(self, obj, index, value, line):
        if isinstance(obj, list):
            i = self.require_int(index, line, "list index")
            if i < 0:
                i += len(obj)
            if i < 0 or i >= len(obj):
                raise SableRuntimeError("list index out of range", line)
            obj[i] = value
            return
        if isinstance(obj, SableMap):
            obj.set(index, value)
            return
        if isinstance(obj, SableObject):
            if not isinstance(index, str):
                raise SableRuntimeError("object fields must be strings", line)
            obj.fields.set(index, value)
            return
        if isinstance(obj, str):
            raise SableRuntimeError("strings are immutable", line)
        raise SableRuntimeError("value does not support item assignment", line)

    def install_builtins(self):
        def register(name, fn, min_args=0, max_args=None):
            self.globals.define(name, Builtin(name, fn, min_args, max_args))

        register("print", self.builtin_print, 0, None)
        register("len", self.builtin_len, 1, 1)
        register("str", self.builtin_str, 1, 1)
        register("num", self.builtin_num, 1, 1)
        register("type", self.builtin_type, 1, 1)
        register("range", self.builtin_range, 1, 3)
        register("push", self.builtin_push, 2, 2)
        register("pop", self.builtin_pop, 1, 1)
        register("keys", self.builtin_keys, 1, 1)
        register("has", self.builtin_has, 2, 2)
        register("input", self.builtin_input, 0, 1)
        register("assert", self.builtin_assert, 1, 2)
        register("sort", self.builtin_sort, 1, 2)
        register("upper", self.builtin_upper, 1, 1)
        register("lower", self.builtin_lower, 1, 1)
        register("join", self.builtin_join, 2, 2)
        register("split", self.builtin_split, 2, 2)
        register("map", self.builtin_map, 2, 2)
        register("filter", self.builtin_filter, 2, 2)
        register("reduce", self.builtin_reduce, 2, 3)
        register("sum", self.builtin_sum, 1, 1)
        register("abs", self.builtin_abs, 1, 1)
        register("min", self.builtin_min, 1, None)
        register("max", self.builtin_max, 1, None)
        register("floor", self.builtin_floor, 1, 1)
        register("ceil", self.builtin_ceil, 1, 1)
        register("round", self.builtin_round, 1, 1)
        register("sqrt", self.builtin_sqrt, 1, 1)
        register("pow", self.builtin_pow, 2, 2)
        register("contains", self.builtin_contains, 2, 2)
        register("index_of", self.builtin_index_of, 2, 2)
        register("slice", self.builtin_slice, 2, 3)
        register("replace", self.builtin_replace, 3, 3)
        register("trim", self.builtin_trim, 1, 1)
        register("starts_with", self.builtin_starts_with, 2, 2)
        register("ends_with", self.builtin_ends_with, 2, 2)
        register("spawn", self.builtin_spawn, 1, None)
        register("wait", self.builtin_wait, 1, 1)
        register("sleep", self.builtin_sleep, 1, 1)

    def builtin_print(self, args, line):
        print(" ".join(to_display(value) for value in args))
        return None

    def builtin_len(self, args, line):
        value = args[0]
        if isinstance(value, (str, list, SableMap)):
            return float(len(value))
        raise SableRuntimeError("len() expects a string, list, or map", line)

    def builtin_str(self, args, line):
        return to_display(args[0])

    def builtin_num(self, args, line):
        value = args[0]
        if is_number(value):
            return value
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise SableRuntimeError(f"cannot convert {value!r} to a number", line)
        raise SableRuntimeError("num() expects a string or number", line)

    def builtin_type(self, args, line):
        value = args[0]
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "list"
        if isinstance(value, SableMap):
            return "map"
        if isinstance(value, Function):
            return "function"
        if isinstance(value, Builtin):
            return "builtin"
        if isinstance(value, BoundMethod):
            return "function"
        if isinstance(value, SableClass):
            return "class"
        if isinstance(value, SableObject):
            return "object"
        if isinstance(value, Task):
            return "task"
        return "unknown"

    def builtin_range(self, args, line):
        if len(args) == 1:
            start, end, step = 0.0, args[0], 1.0
        elif len(args) == 2:
            start, end, step = args[0], args[1], 1.0
        else:
            start, end, step = args[0], args[1], args[2]
        start_i = self.require_int(start, line, "range start")
        end_i = self.require_int(end, line, "range end")
        step_i = self.require_int(step, line, "range step")
        if step_i == 0:
            raise SableRuntimeError("range step cannot be zero", line)
        return [float(i) for i in range(start_i, end_i, step_i)]

    def builtin_push(self, args, line):
        target, value = args
        if not isinstance(target, list):
            raise SableRuntimeError("push() expects a list", line)
        target.append(value)
        return target

    def builtin_pop(self, args, line):
        target = args[0]
        if not isinstance(target, list):
            raise SableRuntimeError("pop() expects a list", line)
        if not target:
            raise SableRuntimeError("cannot pop from an empty list", line)
        return target.pop()

    def builtin_keys(self, args, line):
        target = args[0]
        if not isinstance(target, SableMap):
            raise SableRuntimeError("keys() expects a map", line)
        return target.keys()

    def builtin_has(self, args, line):
        target, key = args
        if not isinstance(target, SableMap):
            raise SableRuntimeError("has() expects a map", line)
        return target.has(key)

    def builtin_input(self, args, line):
        prompt = args[0] if args else ""
        if not isinstance(prompt, str):
            raise SableRuntimeError("input() expects a string prompt", line)
        return input(prompt)

    def builtin_assert(self, args, line):
        if not truthy(args[0]):
            message = to_display(args[1]) if len(args) > 1 else "assertion failed"
            raise SableRuntimeError(message, line)
        return None

    def builtin_sort(self, args, line):
        target = args[0]
        if not isinstance(target, list):
            raise SableRuntimeError("sort() expects a list", line)
        if len(args) == 1:
            try:
                return sorted(target)
            except TypeError:
                raise SableRuntimeError("sort() cannot compare these values", line)
        comparator = args[1]

        def compare(a, b):
            result = self.call_value(comparator, [a, b], line)
            if not is_number(result):
                raise SableRuntimeError("sort comparator must return a number", line)
            return -1 if result < 0 else (1 if result > 0 else 0)

        return sorted(target, key=functools.cmp_to_key(compare))

    def builtin_map(self, args, line):
        items, function = args
        if not isinstance(items, list):
            raise SableRuntimeError("map() expects a list", line)
        return [self.call_value(function, [item], line) for item in items]

    def builtin_filter(self, args, line):
        items, function = args
        if not isinstance(items, list):
            raise SableRuntimeError("filter() expects a list", line)
        return [item for item in items if truthy(self.call_value(function, [item], line))]

    def builtin_reduce(self, args, line):
        items, function = args[0], args[1]
        if not isinstance(items, list):
            raise SableRuntimeError("reduce() expects a list", line)
        if len(args) == 3:
            accumulator = args[2]
            start = 0
        else:
            if not items:
                raise SableRuntimeError("reduce() of an empty list needs an initial value", line)
            accumulator = items[0]
            start = 1
        for item in items[start:]:
            accumulator = self.call_value(function, [accumulator, item], line)
        return accumulator

    def builtin_sum(self, args, line):
        items = args[0]
        if not isinstance(items, list):
            raise SableRuntimeError("sum() expects a list", line)
        total = 0.0
        for item in items:
            if not is_number(item):
                raise SableRuntimeError("sum() expects a list of numbers", line)
            total += item
        return total

    def builtin_abs(self, args, line):
        if not is_number(args[0]):
            raise SableRuntimeError("abs() expects a number", line)
        return abs(args[0])

    def builtin_min(self, args, line):
        values = args[0] if len(args) == 1 and isinstance(args[0], list) else args
        if not values:
            raise SableRuntimeError("min() needs at least one value", line)
        for value in values:
            if not is_number(value):
                raise SableRuntimeError("min() expects numbers", line)
        return min(values)

    def builtin_max(self, args, line):
        values = args[0] if len(args) == 1 and isinstance(args[0], list) else args
        if not values:
            raise SableRuntimeError("max() needs at least one value", line)
        for value in values:
            if not is_number(value):
                raise SableRuntimeError("max() expects numbers", line)
        return max(values)

    def builtin_floor(self, args, line):
        if not is_number(args[0]):
            raise SableRuntimeError("floor() expects a number", line)
        return float(math.floor(args[0]))

    def builtin_ceil(self, args, line):
        if not is_number(args[0]):
            raise SableRuntimeError("ceil() expects a number", line)
        return float(math.ceil(args[0]))

    def builtin_round(self, args, line):
        if not is_number(args[0]):
            raise SableRuntimeError("round() expects a number", line)
        return float(round(args[0]))

    def builtin_sqrt(self, args, line):
        if not is_number(args[0]):
            raise SableRuntimeError("sqrt() expects a number", line)
        if args[0] < 0:
            raise SableRuntimeError("sqrt() of a negative number", line)
        return math.sqrt(args[0])

    def builtin_pow(self, args, line):
        if not (is_number(args[0]) and is_number(args[1])):
            raise SableRuntimeError("pow() expects two numbers", line)
        return math.pow(args[0], args[1])

    def builtin_contains(self, args, line):
        container, value = args
        if isinstance(container, list):
            return any(sable_equal(item, value) for item in container)
        if isinstance(container, str):
            if not isinstance(value, str):
                raise SableRuntimeError("contains() on a string needs a string", line)
            return value in container
        if isinstance(container, SableMap):
            return container.has(value)
        raise SableRuntimeError("contains() expects a list, string, or map", line)

    def builtin_index_of(self, args, line):
        container, value = args
        if isinstance(container, list):
            for index, item in enumerate(container):
                if sable_equal(item, value):
                    return float(index)
            return -1.0
        if isinstance(container, str):
            if not isinstance(value, str):
                raise SableRuntimeError("index_of() on a string needs a string", line)
            return float(container.find(value))
        raise SableRuntimeError("index_of() expects a list or string", line)

    def builtin_slice(self, args, line):
        container = args[0]
        start = self.require_int(args[1], line, "slice start")
        end = None if len(args) == 2 else self.require_int(args[2], line, "slice end")
        if isinstance(container, (list, str)):
            return container[start:end]
        raise SableRuntimeError("slice() expects a list or string", line)

    def builtin_replace(self, args, line):
        text, old, new = args
        if not (isinstance(text, str) and isinstance(old, str) and isinstance(new, str)):
            raise SableRuntimeError("replace() expects three strings", line)
        return text.replace(old, new)

    def builtin_trim(self, args, line):
        if not isinstance(args[0], str):
            raise SableRuntimeError("trim() expects a string", line)
        return args[0].strip()

    def builtin_starts_with(self, args, line):
        text, prefix = args
        if not (isinstance(text, str) and isinstance(prefix, str)):
            raise SableRuntimeError("starts_with() expects two strings", line)
        return text.startswith(prefix)

    def builtin_ends_with(self, args, line):
        text, suffix = args
        if not (isinstance(text, str) and isinstance(suffix, str)):
            raise SableRuntimeError("ends_with() expects two strings", line)
        return text.endswith(suffix)

    def builtin_spawn(self, args, line):
        function = args[0]
        call_args = args[1:]
        if not isinstance(function, (Function, Builtin, BoundMethod)):
            raise SableRuntimeError("spawn() expects a function", line)
        box = {}

        def run():
            try:
                box["value"] = self.call_value(function, call_args, line)
            except BaseException as error:
                box["error"] = error

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return Task(thread, box)

    def builtin_wait(self, args, line):
        task = args[0]
        if not isinstance(task, Task):
            raise SableRuntimeError("wait() expects a task", line)
        task.thread.join()
        if "error" in task.box:
            raise task.box["error"]
        return task.box.get("value")

    def builtin_sleep(self, args, line):
        if not is_number(args[0]):
            raise SableRuntimeError("sleep() expects milliseconds", line)
        time.sleep(max(0.0, args[0] / 1000.0))
        return None

    def builtin_upper(self, args, line):
        if not isinstance(args[0], str):
            raise SableRuntimeError("upper() expects a string", line)
        return args[0].upper()

    def builtin_lower(self, args, line):
        if not isinstance(args[0], str):
            raise SableRuntimeError("lower() expects a string", line)
        return args[0].lower()

    def builtin_join(self, args, line):
        items, separator = args
        if not isinstance(items, list) or not isinstance(separator, str):
            raise SableRuntimeError("join() expects a list and a string", line)
        for item in items:
            if not isinstance(item, str):
                raise SableRuntimeError("join() expects a list of strings", line)
        return separator.join(items)

    def builtin_split(self, args, line):
        text, separator = args
        if not isinstance(text, str) or not isinstance(separator, str):
            raise SableRuntimeError("split() expects two strings", line)
        if separator == "":
            raise SableRuntimeError("split() separator cannot be empty", line)
        return text.split(separator)


def lex(source):
    return Lexer(source).scan()


def parse(source):
    return Parser(lex(source), source).parse()


def interpret(program, base_dir="."):
    return Interpreter(base_dir).run(program)


def run_source(source, base_dir="."):
    program = parse(source)
    Checker().check(program)
    return interpret(program, base_dir)


def format_error(error, source):
    source = error.source or source
    lines = source.splitlines() or [""]
    if error.filename:
        text = f"{error.kind} in {error.filename}: {error.message}"
    else:
        text = f"{error.kind}: {error.message}"
    if 1 <= error.line <= len(lines):
        text += f"\n  line {error.line}: {lines[error.line - 1]}"
        text += "\n  " + " " * max(0, error.col - 1) + "^"
    return text


def brackets_balanced(source):
    depth = 0
    in_string = False
    escaped = False
    i = 0
    while i < len(source):
        c = source[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "/" and i + 1 < len(source) and source[i + 1] == "/":
                while i < len(source) and source[i] != "\n":
                    i += 1
            elif c == "/" and i + 1 < len(source) and source[i + 1] == "*":
                i += 2
                while i + 1 < len(source) and not (source[i] == "*" and source[i + 1] == "/"):
                    i += 1
                i += 1
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
        i += 1
    return depth <= 0 and not in_string


def read_source(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def repl():
    print(f"Sable {VERSION}  (Ctrl-D to quit)")
    interpreter = Interpreter(os.getcwd())
    buffer = ""
    while True:
        prompt = "sable> " if not buffer else "  ... "
        try:
            line = input(prompt)
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            buffer = ""
            continue
        buffer += line + "\n"
        if not brackets_balanced(buffer):
            continue
        try:
            program = parse(buffer)
            Checker().check(program)
            value = interpreter.run(program)
            if value is not None:
                print(to_display(value))
        except SableError as error:
            print(format_error(error, buffer))
        buffer = ""


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) == 1:
        repl()
        return 0
    arg = argv[1]
    if arg in ("-v", "--version"):
        print(f"Sable {VERSION}")
        return 0
    if arg in ("-h", "--help"):
        print("usage: sable [options] [file]")
        print()
        print("  sable              start the REPL")
        print("  sable file.sable   run a program")
        print("  sable --tokens f   print the token stream")
        print("  sable --ast f      print the parsed AST")
        print("  sable --check f    check type annotations")
        print("  sable --verify f   run static verification checks")
        print("  sable -v           print the version")
        return 0
    if arg == "--check":
        if len(argv) < 3:
            print("--check needs a file", file=sys.stderr)
            return 1
        try:
            source = read_source(argv[2])
        except OSError as error:
            print(f"sable: {error}", file=sys.stderr)
            return 1
        try:
            Checker().check(parse(source))
        except SableError as error:
            print(format_error(error, source), file=sys.stderr)
            return 1
        print("ok")
        return 0
    if arg == "--verify":
        if len(argv) < 3:
            print("--verify needs a file", file=sys.stderr)
            return 1
        try:
            source = read_source(argv[2])
        except OSError as error:
            print(f"sable: {error}", file=sys.stderr)
            return 1
        try:
            program = parse(source)
            Checker().check(program)
        except SableError as error:
            print(format_error(error, source), file=sys.stderr)
            return 1
        errors, warnings = Verifier().verify(program)
        for line, message in warnings:
            print(f"{argv[2]}:{line}: warning: {message}")
        for line, message in errors:
            print(f"{argv[2]}:{line}: error: {message}", file=sys.stderr)
        if errors:
            return 1
        print("ok")
        return 0
    if arg in ("--tokens", "--ast"):
        if len(argv) < 3:
            print(f"{arg} needs a file", file=sys.stderr)
            return 1
        try:
            source = read_source(argv[2])
        except OSError as error:
            print(f"sable: {error}", file=sys.stderr)
            return 1
        try:
            if arg == "--tokens":
                for token in lex(source):
                    print(token)
            else:
                import pprint
                pprint.pprint(parse(source))
        except SableError as error:
            print(format_error(error, source), file=sys.stderr)
            return 1
        return 0
    try:
        source = read_source(arg)
    except OSError as error:
        print(f"sable: {error}", file=sys.stderr)
        return 1
    base_dir = os.path.dirname(os.path.abspath(arg))
    try:
        run_source(source, base_dir)
    except SableError as error:
        print(format_error(error, source), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
