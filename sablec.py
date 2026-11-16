#!/usr/bin/env python3
"""Sable to C compiler for the core language."""

import os
import shutil
import subprocess
import sys
import tempfile

import sable


class NativeError(Exception):
    pass


RUNTIME = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

typedef enum { V_NIL, V_BOOL, V_NUM, V_STR } VType;

typedef struct {
    VType type;
    int boolean;
    double num;
    char *str;
} Value;

static Value v_nil(void) {
    Value v;
    v.type = V_NIL;
    v.boolean = 0;
    v.num = 0;
    v.str = NULL;
    return v;
}

static Value v_bool(int b) {
    Value v;
    v.type = V_BOOL;
    v.boolean = b ? 1 : 0;
    v.num = 0;
    v.str = NULL;
    return v;
}

static Value v_num(double n) {
    Value v;
    v.type = V_NUM;
    v.boolean = 0;
    v.num = n;
    v.str = NULL;
    return v;
}

static Value v_str(const char *s) {
    Value v;
    v.type = V_STR;
    v.boolean = 0;
    v.num = 0;
    v.str = malloc(strlen(s) + 1);
    strcpy(v.str, s);
    return v;
}

static void v_fail(const char *message) {
    fprintf(stderr, "RuntimeError: %s\n", message);
    exit(1);
}

static int v_truthy(Value v) {
    if (v.type == V_NIL) return 0;
    if (v.type == V_BOOL) return v.boolean;
    return 1;
}

static double v_as_num(Value v) {
    if (v.type != V_NUM) v_fail("expected a number");
    return v.num;
}

static const char *v_text(Value v) {
    char *out;
    if (v.type == V_NIL) return "nil";
    if (v.type == V_BOOL) return v.boolean ? "true" : "false";
    if (v.type == V_STR) return v.str;
    out = malloc(64);
    if (v.num == floor(v.num) && fabs(v.num) < 1e16) {
        snprintf(out, 64, "%lld", (long long)v.num);
    } else {
        snprintf(out, 64, "%.15g", v.num);
    }
    return out;
}

static Value v_add(Value a, Value b) {
    if (a.type == V_NUM && b.type == V_NUM) return v_num(a.num + b.num);
    if (a.type == V_STR && b.type == V_STR) {
        size_t size = strlen(a.str) + strlen(b.str) + 1;
        char *text = malloc(size);
        strcpy(text, a.str);
        strcat(text, b.str);
        Value v;
        v.type = V_STR;
        v.boolean = 0;
        v.num = 0;
        v.str = text;
        return v;
    }
    v_fail("cannot add these values");
    return v_nil();
}

static Value v_sub(Value a, Value b) {
    return v_num(v_as_num(a) - v_as_num(b));
}

static Value v_mul(Value a, Value b) {
    return v_num(v_as_num(a) * v_as_num(b));
}

static Value v_div(Value a, Value b) {
    double right = v_as_num(b);
    if (right == 0) v_fail("division by zero");
    return v_num(v_as_num(a) / right);
}

static Value v_mod(Value a, Value b) {
    double right = v_as_num(b);
    if (right == 0) v_fail("division by zero");
    return v_num(fmod(v_as_num(a), right));
}

static Value v_neg(Value a) {
    return v_num(-v_as_num(a));
}

static Value v_not(Value a) {
    return v_bool(!v_truthy(a));
}

static Value v_eq(Value a, Value b) {
    if (a.type != b.type) return v_bool(0);
    if (a.type == V_NIL) return v_bool(1);
    if (a.type == V_BOOL) return v_bool(a.boolean == b.boolean);
    if (a.type == V_NUM) return v_bool(a.num == b.num);
    return v_bool(strcmp(a.str, b.str) == 0);
}

static Value v_ne(Value a, Value b) {
    return v_bool(!v_truthy(v_eq(a, b)));
}

static int v_compare(Value a, Value b) {
    if (a.type == V_NUM && b.type == V_NUM) {
        return (a.num < b.num) ? -1 : (a.num > b.num ? 1 : 0);
    }
    if (a.type == V_STR && b.type == V_STR) {
        return strcmp(a.str, b.str);
    }
    v_fail("cannot compare these values");
    return 0;
}

static Value v_lt(Value a, Value b) { return v_bool(v_compare(a, b) < 0); }
static Value v_le(Value a, Value b) { return v_bool(v_compare(a, b) <= 0); }
static Value v_gt(Value a, Value b) { return v_bool(v_compare(a, b) > 0); }
static Value v_ge(Value a, Value b) { return v_bool(v_compare(a, b) >= 0); }

static Value v_len(Value a) {
    if (a.type != V_STR) v_fail("len() expects a string");
    return v_num((double)strlen(a.str));
}

static Value v_str_of(Value a) {
    return v_str(v_text(a));
}

static Value v_num_of(Value a) {
    if (a.type == V_NUM) return a;
    if (a.type == V_STR) {
        char *end;
        double n = strtod(a.str, &end);
        if (end == a.str || *end != '\0') v_fail("cannot convert string to a number");
        return v_num(n);
    }
    v_fail("num() expects a string or number");
    return v_nil();
}

static Value v_print0(void) {
    printf("\n");
    return v_nil();
}

static Value v_print1(Value a) {
    printf("%s\n", v_text(a));
    return v_nil();
}

static Value v_print2(Value a, Value b) {
    printf("%s %s\n", v_text(a), v_text(b));
    return v_nil();
}

static Value v_print3(Value a, Value b, Value c) {
    printf("%s %s %s\n", v_text(a), v_text(b), v_text(c));
    return v_nil();
}
'''


def c_string(text):
    out = ['"']
    for ch in text:
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\t':
            out.append('\\t')
        elif ch == '\r':
            out.append('\\r')
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def c_ident(name):
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)


class CCompiler:
    def __init__(self, program):
        self.program = program
        self.globals = {}
        self.functions = {}
        self.scopes = []
        self.consts = set()
        self.node_names = {}
        self.counter = 0
        self.lines = []
        self.current_function = None

    def unique(self, prefix):
        self.counter += 1
        return f"{prefix}_{self.counter}"

    def emit(self, line=""):
        self.lines.append(line)

    def compile(self):
        self.collect_top_level()
        self.emit(RUNTIME)
        for cname in self.globals.values():
            self.emit(f"Value {cname};")
        for name, params in self.functions.items():
            args = ", ".join("Value" for _ in params)
            self.emit(f"Value {self.function_name(name)}({args});")
        for stmt in self.program.statements:
            if isinstance(stmt, sable.FnDecl):
                self.compile_function(stmt)
        self.emit("int main(void) {")
        for stmt in self.program.statements:
            if isinstance(stmt, sable.FnDecl):
                continue
            if isinstance(stmt, (sable.Let, sable.Const)):
                target = self.node_names[id(stmt)]
                self.emit(f"    {target} = {self.expression(stmt.value)};")
            else:
                self.statement(stmt)
        self.emit("    return 0;")
        self.emit("}")
        return "\n".join(self.lines)

    def collect_top_level(self):
        for stmt in self.program.statements:
            if isinstance(stmt, (sable.Let, sable.Const)):
                name = self.unique("g_" + c_ident(stmt.name))
                self.globals[stmt.name] = name
                self.node_names[id(stmt)] = name
                if isinstance(stmt, sable.Const):
                    self.consts.add(name)
            elif isinstance(stmt, sable.FnDecl):
                self.functions[stmt.name] = stmt.params
            elif isinstance(stmt, sable.Import):
                raise NativeError("the native backend does not support imports yet")
            elif isinstance(stmt, sable.ClassDecl):
                raise NativeError("the native backend does not support classes yet")

    def function_name(self, name):
        return "fn_" + c_ident(name)

    def compile_function(self, stmt):
        saved = self.scopes
        saved_consts = set(self.consts)
        saved_function = self.current_function
        self.current_function = stmt.name
        self.scopes = [{}]
        args = []
        for param in stmt.params:
            cname = self.unique("p_" + c_ident(param))
            self.scopes[-1][param] = cname
            args.append(f"Value {cname}")
        self.emit(f"Value {self.function_name(stmt.name)}({', '.join(args)}) {{")
        for child in stmt.body.statements:
            self.statement(child, indent="    ")
        self.emit("    return v_nil();")
        self.emit("}")
        self.scopes = saved
        self.consts = saved_consts
        self.current_function = saved_function

    def statement(self, stmt, indent=""):
        if isinstance(stmt, sable.Let) or isinstance(stmt, sable.Const):
            cname = self.unique("l_" + c_ident(stmt.name))
            self.scopes[-1][stmt.name] = cname
            if isinstance(stmt, sable.Const):
                self.consts.add(cname)
            self.emit(f"{indent}Value {cname} = {self.expression(stmt.value)};")
        elif isinstance(stmt, sable.ExprStmt):
            self.emit(f"{indent}(void)({self.expression(stmt.expr)});")
        elif isinstance(stmt, sable.Block):
            self.emit(f"{indent}{{")
            self.scopes.append({})
            for child in stmt.statements:
                self.statement(child, indent + "    ")
            self.scopes.pop()
            self.emit(f"{indent}}}")
        elif isinstance(stmt, sable.If):
            self.emit(f"{indent}if (v_truthy({self.expression(stmt.cond)})) {{")
            self.scopes.append({})
            for child in stmt.then_branch.statements:
                self.statement(child, indent + "    ")
            self.scopes.pop()
            if stmt.else_branch is not None:
                self.emit(f"{indent}}} else {{")
                self.scopes.append({})
                if isinstance(stmt.else_branch, sable.Block):
                    for child in stmt.else_branch.statements:
                        self.statement(child, indent + "    ")
                else:
                    self.statement(stmt.else_branch, indent + "    ")
                self.scopes.pop()
            self.emit(f"{indent}}}")
        elif isinstance(stmt, sable.While):
            self.emit(f"{indent}while (v_truthy({self.expression(stmt.cond)})) {{")
            self.scopes.append({})
            for child in stmt.body.statements:
                self.statement(child, indent + "    ")
            self.scopes.pop()
            self.emit(f"{indent}}}")
        elif isinstance(stmt, sable.For):
            self.compile_for(stmt, indent)
        elif isinstance(stmt, sable.Return):
            if self.current_function is None:
                raise NativeError("'return' outside a function")
            if stmt.value is None:
                self.emit(f"{indent}return v_nil();")
            else:
                self.emit(f"{indent}return {self.expression(stmt.value)};")
        elif isinstance(stmt, sable.Break):
            self.emit(f"{indent}break;")
        elif isinstance(stmt, sable.Continue):
            self.emit(f"{indent}continue;")
        else:
            raise NativeError(
                f"the native backend does not support {type(stmt).__name__} yet")

    def compile_for(self, stmt, indent):
        iterable = stmt.iterable
        if not (isinstance(iterable, sable.Call)
                and isinstance(iterable.callee, sable.Var)
                and iterable.callee.name == "range"):
            raise NativeError("the native backend only supports for..in range(...) yet")
        args = iterable.args
        if len(args) == 1:
            start, end, step = "v_num(0)", self.expression(args[0]), "v_num(1)"
        elif len(args) == 2:
            start, end, step = self.expression(args[0]), self.expression(args[1]), "v_num(1)"
        elif len(args) == 3:
            start = self.expression(args[0])
            end = self.expression(args[1])
            step = self.expression(args[2])
        else:
            raise NativeError("range() takes one to three arguments")
        start_var = self.unique("start")
        end_var = self.unique("end")
        step_var = self.unique("step")
        index_var = self.unique("i")
        self.emit(f"{indent}{{")
        self.emit(f"{indent}    double {start_var} = v_as_num({start});")
        self.emit(f"{indent}    double {end_var} = v_as_num({end});")
        self.emit(f"{indent}    double {step_var} = v_as_num({step});")
        self.emit(f"{indent}    if ({step_var} == 0) v_fail(\"range step cannot be zero\");")
        self.emit(f"{indent}    for (double {index_var} = {start_var}; "
                  f"({step_var} > 0 ? {index_var} < {end_var} : {index_var} > {end_var}); "
                  f"{index_var} += {step_var}) {{")
        self.scopes.append({})
        loop_var = self.unique("l_" + c_ident(stmt.var))
        self.scopes[-1][stmt.var] = loop_var
        self.emit(f"{indent}        Value {loop_var} = v_num({index_var});")
        for child in stmt.body.statements:
            self.statement(child, indent + "        ")
        self.scopes.pop()
        self.emit(f"{indent}    }}")
        self.emit(f"{indent}}}")

    def expression(self, expr):
        if isinstance(expr, sable.Literal):
            value = expr.value
            if value is None:
                return "v_nil()"
            if isinstance(value, bool):
                return f"v_bool({1 if value else 0})"
            if isinstance(value, float):
                return f"v_num({repr(value)})"
            if isinstance(value, str):
                return f"v_str({c_string(value)})"
        if isinstance(expr, sable.Var):
            cname = self.lookup(expr.name)
            return cname
        if isinstance(expr, sable.Unary):
            operand = self.expression(expr.operand)
            if expr.op == "not":
                return f"v_not({operand})"
            return f"v_neg({operand})"
        if isinstance(expr, sable.Binary):
            left = self.expression(expr.left)
            right = self.expression(expr.right)
            operations = {
                "+": "v_add", "-": "v_sub", "*": "v_mul", "/": "v_div", "%": "v_mod",
                "==": "v_eq", "!=": "v_ne", "<": "v_lt", "<=": "v_le",
                ">": "v_gt", ">=": "v_ge",
            }
            if expr.op not in operations:
                raise NativeError(f"the native backend does not support operator '{expr.op}'")
            return f"{operations[expr.op]}({left}, {right})"
        if isinstance(expr, sable.Logical):
            left = self.expression(expr.left)
            right = self.expression(expr.right)
            if expr.op == "and":
                return f"(v_truthy({left}) ? {right} : {left})"
            return f"(v_truthy({left}) ? {left} : {right})"
        if isinstance(expr, sable.Assign):
            if not isinstance(expr.target, sable.Var):
                raise NativeError("the native backend does not support index assignment yet")
            cname = self.lookup(expr.target.name)
            if cname in self.consts:
                raise NativeError(f"cannot assign to constant '{expr.target.name}'")
            value = self.expression(expr.value)
            if expr.op == "=":
                return f"({cname} = {value})"
            operations = {"+=": "v_add", "-=": "v_sub", "*=": "v_mul", "/=": "v_div"}
            if expr.op not in operations:
                raise NativeError(f"the native backend does not support '{expr.op}'")
            return f"({cname} = {operations[expr.op]}({cname}, {value}))"
        if isinstance(expr, sable.Call):
            if not isinstance(expr.callee, sable.Var):
                raise NativeError("the native backend only supports simple function calls yet")
            name = expr.callee.name
            args = [self.expression(arg) for arg in expr.args]
            if name in self.functions:
                expected = len(self.functions[name])
                if len(args) != expected:
                    raise NativeError(f"{name}() expects {expected} argument(s)")
                return f"{self.function_name(name)}({', '.join(args)})"
            if name == "print":
                if len(args) == 0:
                    return "v_print0()"
                if len(args) <= 3:
                    return f"v_print{len(args)}({', '.join(args)})"
                raise NativeError("the native backend supports print() with up to three arguments")
            if name == "str" and len(args) == 1:
                return f"v_str_of({args[0]})"
            if name == "num" and len(args) == 1:
                return f"v_num_of({args[0]})"
            if name == "len" and len(args) == 1:
                return f"v_len({args[0]})"
            raise NativeError(f"the native backend does not support builtin '{name}' yet")
        if isinstance(expr, sable.ListLit):
            raise NativeError("the native backend does not support lists yet")
        if isinstance(expr, sable.MapLit):
            raise NativeError("the native backend does not support maps yet")
        if isinstance(expr, sable.FnExpr):
            raise NativeError("the native backend does not support anonymous functions yet")
        if isinstance(expr, sable.Index):
            raise NativeError("the native backend does not support indexing yet")
        if isinstance(expr, sable.Pipe):
            raise NativeError("the native backend does not support pipes yet")
        if isinstance(expr, sable.New):
            raise NativeError("the native backend does not support classes yet")
        raise NativeError(
            f"the native backend does not support {type(expr).__name__} yet")

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if name in self.globals:
            return self.globals[name]
        raise NativeError(f"undefined variable '{name}'")


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) < 2:
        print("usage: sablec [options] file.sable")
        print("  -o FILE   write the executable to FILE")
        print("  --run     run the executable after building")
        return 1
    path = argv[1]
    output = os.path.splitext(path)[0]
    run = False
    index = 2
    while index < len(argv):
        if argv[index] == "-o" and index + 1 < len(argv):
            output = argv[index + 1]
            index += 2
        elif argv[index] == "--run":
            run = True
            index += 1
        else:
            print(f"sablec: unknown option {argv[index]}", file=sys.stderr)
            return 1
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except OSError as error:
        print(f"sablec: {error}", file=sys.stderr)
        return 1
    try:
        program = sable.parse(source)
        sable.Checker().check(program)
        code = CCompiler(program).compile()
    except (sable.SableError, NativeError) as error:
        print(f"sablec: {error}", file=sys.stderr)
        return 1
    handle = tempfile.NamedTemporaryFile("w", suffix=".c", delete=False)
    try:
        handle.write(code)
        handle.close()
        cc = os.environ.get("CC", "cc")
        if shutil.which(cc) is None:
            print(f"sablec: C compiler '{cc}' not found", file=sys.stderr)
            return 1
        command = [cc, "-O2", "-o", output, handle.name]
        if os.name != "nt":
            command.append("-lm")
        result = subprocess.run(command)
        if result.returncode != 0:
            return result.returncode
    finally:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
    if run:
        return subprocess.run([output]).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
