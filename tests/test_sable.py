import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sable


def run(source):
    output = io.StringIO()
    error = None
    with contextlib.redirect_stdout(output):
        try:
            sable.run_source(source)
        except sable.SableError as exc:
            error = exc
    return output.getvalue(), error


class TestExpressions(unittest.TestCase):
    def test_arithmetic(self):
        out, err = run("print(1 + 2 * 3); print((1 + 2) * 3); print(7 / 2); print(7 % 2); print(-5 + 2);")
        self.assertIsNone(err)
        self.assertEqual(out, "7\n9\n3.5\n1\n-3\n")

    def test_strings(self):
        out, err = run('print("a" + "b"); print(len("hello")); print("hello"[1]); print("hello"[-1]);')
        self.assertIsNone(err)
        self.assertEqual(out, "ab\n5\ne\no\n")

    def test_escapes(self):
        out, err = run('print("line\\nnext"); print("tab\\there"); print("quote\\"here");')
        self.assertIsNone(err)
        self.assertEqual(out, 'line\nnext\ntab\there\nquote"here\n')

    def test_equality(self):
        out, err = run('print(1 == 1); print(1 == 2); print("a" != "b"); print(nil == nil); print([1, 2] == [1, 2]);')
        self.assertIsNone(err)
        self.assertEqual(out, "true\nfalse\ntrue\ntrue\ntrue\n")

    def test_logic(self):
        out, err = run('print(true and false); print(false or 5); print(not nil);')
        self.assertIsNone(err)
        self.assertEqual(out, "false\n5\ntrue\n")

    def test_precedence(self):
        out, err = run("print(2 + 3 * 4 - 1); print(10 / 2 + 3);")
        self.assertIsNone(err)
        self.assertEqual(out, "13\n8\n")


class TestStatements(unittest.TestCase):
    def test_variables_and_scope(self):
        out, err = run("let x = 10; { let x = 20; print(x); } print(x); x = x + 1; print(x);")
        self.assertIsNone(err)
        self.assertEqual(out, "20\n10\n11\n")

    def test_if_else(self):
        out, err = run('let n = 5; if n > 10 { print("big"); } else if n > 3 { print("mid"); } else { print("small"); }')
        self.assertIsNone(err)
        self.assertEqual(out, "mid\n")

    def test_while_break_continue(self):
        out, err = run("let i = 0; while i < 10 { i = i + 1; if i % 2 == 0 { continue; } if i > 7 { break; } print(i); }")
        self.assertIsNone(err)
        self.assertEqual(out, "1\n3\n5\n7\n")

    def test_for(self):
        out, err = run('for x in [1, 2, 3] { print(x); } for c in "ab" { print(c); } for i in range(3) { print(i); }')
        self.assertIsNone(err)
        self.assertEqual(out, "1\n2\n3\na\nb\n0\n1\n2\n")

    def test_compound_assignment(self):
        out, err = run("let x = 1; x += 2; x *= 3; print(x);")
        self.assertIsNone(err)
        self.assertEqual(out, "9\n")

    def test_comments(self):
        out, err = run("// a comment\nlet x = 1; /* block\ncomment */ print(x);")
        self.assertIsNone(err)
        self.assertEqual(out, "1\n")


class TestFunctions(unittest.TestCase):
    def test_recursion(self):
        out, err = run("fn fact(n) { if n <= 1 { return 1; } return n * fact(n - 1); } print(fact(5));")
        self.assertIsNone(err)
        self.assertEqual(out, "120\n")

    def test_closures(self):
        out, err = run("fn make_counter() { let n = 0; fn next() { n = n + 1; return n; } return next; } let c = make_counter(); print(c()); print(c());")
        self.assertIsNone(err)
        self.assertEqual(out, "1\n2\n")

    def test_function_expression(self):
        out, err = run("let add = fn(a, b) { return a + b; }; print(add(2, 3));")
        self.assertIsNone(err)
        self.assertEqual(out, "5\n")

    def test_implicit_nil(self):
        out, err = run("fn f() { let x = 1; } print(f());")
        self.assertIsNone(err)
        self.assertEqual(out, "nil\n")


class TestCollections(unittest.TestCase):
    def test_lists(self):
        out, err = run("let a = [1, 2, 3]; a[0] = 10; a[-1] = 30; print(a); print(len(a)); push(a, 4); print(pop(a)); print(a);")
        self.assertIsNone(err)
        self.assertEqual(out, "[10, 2, 30]\n3\n4\n[10, 2, 30]\n")

    def test_maps(self):
        out, err = run('let m = {"a": 1, "b": 2}; print(m["a"]); m["c"] = 3; print(len(m)); print(has(m, "c")); print(keys(m)); print(m);')
        self.assertIsNone(err)
        self.assertEqual(out, '1\n3\ntrue\n["a", "b", "c"]\n{"a": 1, "b": 2, "c": 3}\n')

    def test_builtins(self):
        out, err = run('print(str(12)); print(num("3.5")); print(type(nil)); print(type([])); print(type({})); print(upper("hi")); print(lower("HI")); print(join(["a", "b"], "-")); print(split("a-b", "-")); print(sort([3, 1, 2]));')
        self.assertIsNone(err)
        self.assertEqual(out, '12\n3.5\nnil\nlist\nmap\nHI\nhi\na-b\n["a", "b"]\n[1, 2, 3]\n')

    def test_map_in_expression(self):
        out, err = run('print({"a": 1}["a"]);')
        self.assertIsNone(err)
        self.assertEqual(out, "1\n")


class TestAdvanced(unittest.TestCase):
    def test_dot_access(self):
        out, err = run('let m = {"name": "ana", "age": 15}; print(m.name); m.age = m.age + 1; m.age += 1; print(m.age);')
        self.assertIsNone(err)
        self.assertEqual(out, "ana\n17\n")

    def test_const(self):
        out, err = run("const x = 1; print(x); x = 2;")
        self.assertIsNotNone(err)
        self.assertIn("constant 'x'", err.message)

    def test_try_throw(self):
        out, err = run('try { throw "boom"; } catch e { print(e); }')
        self.assertIsNone(err)
        self.assertEqual(out, "boom\n")

    def test_try_runtime_error(self):
        out, err = run("try { print(1 / 0); } catch e { print(e.message); }")
        self.assertIsNone(err)
        self.assertEqual(out, "division by zero\n")

    def test_try_does_not_catch_return(self):
        out, err = run("fn f() { try { return 1; } catch e { return 2; } } print(f());")
        self.assertIsNone(err)
        self.assertEqual(out, "1\n")

    def test_try_does_not_catch_break(self):
        out, err = run('for i in [1] { try { break; } catch e { print("caught"); } } print("done");')
        self.assertIsNone(err)
        self.assertEqual(out, "done\n")

    def test_uncaught_throw(self):
        out, err = run('throw "oops";')
        self.assertIsNotNone(err)
        self.assertIn("uncaught: oops", err.message)

    def test_match_binding(self):
        source = 'fn describe(x) { match x { 1 => return "one"; 2 => return "two"; n => return "many: " + str(n); } } print(describe(1)); print(describe(2)); print(describe(9));'
        out, err = run(source)
        self.assertIsNone(err)
        self.assertEqual(out, "one\ntwo\nmany: 9\n")

    def test_match_wildcard(self):
        out, err = run('match 5 { 1 => print("one"); _ => print("other"); }')
        self.assertIsNone(err)
        self.assertEqual(out, "other\n")

    def test_match_block(self):
        out, err = run('match 2 { 2 => { print("two"); print("!"); } _ => print("no"); }')
        self.assertIsNone(err)
        self.assertEqual(out, "two\n!\n")

    def test_pipe_into_call(self):
        source = 'let nums = [1, 2, 3, 4]; print(nums |> filter(fn(n) { return n % 2 == 0; }) |> map(fn(n) { return n * 10; }));'
        out, err = run(source)
        self.assertIsNone(err)
        self.assertEqual(out, "[20, 40]\n")

    def test_pipe(self):
        out, err = run("fn double(n) { return n * 2; } print(5 |> double); print(5 |> double |> double); print(1 + 2 |> double);")
        self.assertIsNone(err)
        self.assertEqual(out, "10\n20\n6\n")

    def test_higher_order_builtins(self):
        source = ('print(map([1, 2, 3], fn(n) { return n * 2; }));'
                  'print(filter([1, 2, 3, 4], fn(n) { return n % 2 == 0; }));'
                  'print(reduce([1, 2, 3], fn(a, b) { return a + b; }));'
                  'print(reduce([1, 2, 3], fn(a, b) { return a + b; }, 10));'
                  'print(sum([1, 2, 3]));')
        out, err = run(source)
        self.assertIsNone(err)
        self.assertEqual(out, "[2, 4, 6]\n[2, 4]\n6\n16\n6\n")

    def test_math_builtins(self):
        source = ('print(abs(-5)); print(min([3, 1, 2])); print(max([3, 1, 2]));'
                  'print(min(3, 1, 2)); print(max(3, 1, 2));'
                  'print(floor(3.7)); print(ceil(3.2)); print(round(3.5));'
                  'print(sqrt(9)); print(pow(2, 3));')
        out, err = run(source)
        self.assertIsNone(err)
        self.assertEqual(out, "5\n1\n3\n1\n3\n3\n4\n4\n3\n8\n")

    def test_collection_builtins(self):
        source = ('print(contains([1, 2], 2)); print(contains("hello", "ell"));'
                  'print(contains({"a": 1}, "a"));'
                  'print(index_of([1, 2, 3], 2)); print(index_of("hello", "l"));'
                  'print(slice([1, 2, 3, 4], 1, 3)); print(slice("hello", 1, 3));'
                  'print(replace("a-b-c", "-", "+")); print(trim("  hi  "));'
                  'print(starts_with("hello", "he")); print(ends_with("hello", "lo"));')
        out, err = run(source)
        self.assertIsNone(err)
        self.assertEqual(out, "true\ntrue\ntrue\n1\n2\n[2, 3]\nel\na+b+c\nhi\ntrue\ntrue\n")

    def test_sort_comparator(self):
        source = ('print(sort([3, 1, 2], fn(a, b) { return a - b; }));'
                  'print(sort([3, 1, 2], fn(a, b) { return b - a; }));')
        out, err = run(source)
        self.assertIsNone(err)
        self.assertEqual(out, "[1, 2, 3]\n[3, 2, 1]\n")


class TestTypes(unittest.TestCase):
    def test_annotations_run(self):
        source = 'let x: number = 1; const name: string = "ana"; fn add(a: number, b: number): number { return a + b; } print(add(x, 2)); print(name);'
        out, err = run(source)
        self.assertIsNone(err)
        self.assertEqual(out, "3\nana\n")

    def test_bad_initializer(self):
        out, err = run('let x: number = "a";')
        self.assertIsNotNone(err)
        self.assertIn("cannot initialize 'x'", err.message)

    def test_bad_assignment(self):
        out, err = run('let x: number = 1; x = "a";')
        self.assertIsNotNone(err)
        self.assertIn("cannot assign to 'x'", err.message)

    def test_bad_return(self):
        out, err = run('fn f(): number { return "a"; } print(f());')
        self.assertIsNotNone(err)
        self.assertIn("return value", err.message)

    def test_bad_argument(self):
        out, err = run('fn f(a: number) { return a; } f("a");')
        self.assertIsNotNone(err)
        self.assertIn("argument to f()", err.message)

    def test_bad_operator(self):
        out, err = run('let x: number = 1; print(x + "a");')
        self.assertIsNotNone(err)
        self.assertIn("cannot add number and string", err.message)

    def test_any_type(self):
        out, err = run('let x: any = "a"; x = 1; print(x);')
        self.assertIsNone(err)
        self.assertEqual(out, "1\n")

    def test_function_expression_annotation(self):
        out, err = run("let f = fn(a: number): number { return a * 2; }; print(f(3));")
        self.assertIsNone(err)
        self.assertEqual(out, "6\n")

    def test_collection_annotations(self):
        out, err = run('let xs: list = [1, 2]; let m: map = {"a": 1}; print(xs); print(m);')
        self.assertIsNone(err)
        self.assertEqual(out, "[1, 2]\n{\"a\": 1}\n")


class TestModulesAndMaps(unittest.TestCase):
    def test_non_string_map_keys(self):
        source = 'let m = {1: "one", true: "yes", nil: "none", "a": 1}; print(m[1]); print(m[true]); print(m[nil]); print(m["a"]); m[2] = "two"; print(len(m)); print(keys(m)); print(m);'
        out, err = run(source)
        self.assertIsNone(err)
        self.assertEqual(out, 'one\nyes\nnone\n1\n5\n[1, true, nil, "a", 2]\n{1: "one", true: "yes", nil: "none", "a": 1, 2: "two"}\n')

    def test_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "helpers.sable"), "w") as handle:
                handle.write('fn double(n) { return n * 2; }\nlet version = "1.0";\n')
            source = 'import "helpers.sable"; print(double(21)); print(version);'
            output = io.StringIO()
            error = None
            with contextlib.redirect_stdout(output):
                try:
                    sable.run_source(source, tmp)
                except sable.SableError as exc:
                    error = exc
            self.assertIsNone(error)
            self.assertEqual(output.getvalue(), "42\n1.0\n")

    def test_import_runs_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "helpers.sable"), "w") as handle:
                handle.write('print("loaded");\nfn double(n) { return n * 2; }\n')
            source = 'import "helpers.sable"; import "helpers.sable"; print(double(5));'
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                sable.run_source(source, tmp)
            self.assertEqual(output.getvalue(), "loaded\n10\n")

    def test_import_error_reports_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "bad.sable"), "w") as handle:
                handle.write("let x = ;\n")
            try:
                sable.run_source('import "bad.sable";', tmp)
            except sable.SableError as error:
                self.assertTrue(error.filename.endswith("bad.sable"))
            else:
                self.fail("expected an import error")


class TestRepl(unittest.TestCase):
    def test_state_persists(self):
        inputs = iter(["let x = 2;", "x * 3;", "fn f(n) { return n + 1; }", "f(41);"])

        def fake_input(prompt=""):
            try:
                return next(inputs)
            except StopIteration:
                raise EOFError

        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch("builtins.input", fake_input):
            sable.repl()
        text = output.getvalue()
        self.assertIn("6", text)
        self.assertIn("42", text)


class TestErrors(unittest.TestCase):
    def test_undefined_variable(self):
        out, err = run("print(missing);")
        self.assertIsNotNone(err)
        self.assertIn("undefined variable 'missing'", err.message)

    def test_type_error(self):
        out, err = run('print(1 + "a");')
        self.assertIsNotNone(err)
        self.assertIn("cannot add", err.message)

    def test_division_by_zero(self):
        out, err = run("print(1 / 0);")
        self.assertIsNotNone(err)
        self.assertIn("division by zero", err.message)

    def test_syntax_error(self):
        out, err = run("let x = ;")
        self.assertIsNotNone(err)
        self.assertIsInstance(err, sable.SableSyntaxError)

    def test_arity_error(self):
        out, err = run("fn f(a) { return a; } f();")
        self.assertIsNotNone(err)
        self.assertIn("expects 1 argument", err.message)

    def test_index_error(self):
        out, err = run("let a = [1]; print(a[5]);")
        self.assertIsNotNone(err)
        self.assertIn("out of range", err.message)

    def test_string_immutable(self):
        out, err = run('let s = "a"; s[0] = "b";')
        self.assertIsNotNone(err)
        self.assertIn("immutable", err.message)

    def test_break_outside_loop(self):
        out, err = run("break;")
        self.assertIsNotNone(err)
        self.assertIn("outside a loop", err.message)

    def test_stack_overflow(self):
        out, err = run("fn loop(n) { return loop(n + 1); } loop(0);")
        self.assertIsNotNone(err)
        self.assertIn("stack overflow", err.message)

    def test_return_outside_function(self):
        out, err = run("return 1;")
        self.assertIsNotNone(err)
        self.assertIn("outside a function", err.message)


if __name__ == "__main__":
    unittest.main()
