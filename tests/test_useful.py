import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import sable


def run(source):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        sable.run_source(source)
    return output.getvalue()


class TestUsefulBuiltins(unittest.TestCase):
    def test_json_roundtrip(self):
        source = ('let data = {"a": [1, true, nil, "x"], "b": {"c": 2}}; '
                  'let copy = json_decode(json_encode(data)); '
                  'print(copy.a[0]); print(copy.b.c); print(copy.a[3]);')
        self.assertEqual(run(source), "1\n2\nx\n")

    def test_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.txt")
            source = (f'write_file({json.dumps(path)}, "hello"); '
                      f'append_file({json.dumps(path)}, " world"); '
                      f'print(read_file({json.dumps(path)})); '
                      f'print(file_exists({json.dumps(path)})); '
                      f'print(list_dir({json.dumps(tmp)}));')
            self.assertEqual(run(source), 'hello world\ntrue\n["data.txt"]\n')

    def test_getenv(self):
        os.environ["SABLE_TEST_VAR"] = "yes"
        try:
            self.assertEqual(run('print(getenv("SABLE_TEST_VAR"));'), "yes\n")
        finally:
            del os.environ["SABLE_TEST_VAR"]

    def test_clock_and_random(self):
        out = run('print(type(clock())); print(type(random())); print(random_int(1, 1));')
        self.assertEqual(out, "number\nnumber\n1\n")


class TestRunner(unittest.TestCase):
    def test_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "pass.sable"), "w") as handle:
                handle.write('print("ok");')
            with open(os.path.join(tmp, "fail.sable"), "w") as handle:
                handle.write('throw "bad";')
            result = subprocess.run(
                [sys.executable, os.path.join(ROOT, "sable.py"), "--test", tmp],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PASS", result.stdout)
            self.assertIn("FAIL", result.stdout)

    def test_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exit.sable")
            with open(path, "w") as handle:
                handle.write("exit(3);")
            result = subprocess.run(
                [sys.executable, os.path.join(ROOT, "sable.py"), path],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 3)

    def test_todo_example(self):
        script = os.path.join(ROOT, "examples", "todo.sable")
        with tempfile.TemporaryDirectory() as tmp:
            def todo(*args):
                return subprocess.run(
                    [sys.executable, os.path.join(ROOT, "sable.py"), script, *args],
                    capture_output=True, text=True, cwd=tmp)
            self.assertEqual(todo("add", "buy", "milk").stdout.strip(), "added")
            self.assertEqual(todo("add", "write", "code").stdout.strip(), "added")
            listing = todo("list").stdout
            self.assertIn("0 [ ] buy milk", listing)
            self.assertEqual(todo("done", "0").stdout.strip(), "done")
            self.assertIn("0 [x] buy milk", todo("list").stdout)
            self.assertEqual(todo("clear").stdout.strip(), "cleared")


if __name__ == "__main__":
    unittest.main()
