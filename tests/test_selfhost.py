import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELFHOST = os.path.join(ROOT, "selfhost", "sable.sable")
sys.path.insert(0, ROOT)
import sable


class TestSelfHost(unittest.TestCase):
    def compare(self, source):
        host_output = io.StringIO()
        with contextlib.redirect_stdout(host_output):
            sable.run_source(source)
        handle = tempfile.NamedTemporaryFile("w", suffix=".sable", delete=False)
        try:
            handle.write(source)
            handle.close()
            result = subprocess.run(
                [sys.executable, os.path.join(ROOT, "sable.py"), SELFHOST, handle.name],
                capture_output=True, text=True)
        finally:
            os.unlink(handle.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, host_output.getvalue())

    def test_selfhost_checks(self):
        with open(SELFHOST, "r", encoding="utf-8") as handle:
            source = handle.read()
        sable.Checker().check(sable.parse(source))

    def test_fizzbuzz(self):
        self.compare('for i in range(1, 21) { if i % 15 == 0 { print("FizzBuzz"); } else if i % 3 == 0 { print("Fizz"); } else if i % 5 == 0 { print("Buzz"); } else { print(i); } }')

    def test_fib(self):
        self.compare('fn fib(n) { if n < 2 { return n; } return fib(n - 1) + fib(n - 2); } for i in range(10) { print(fib(i)); }')

    def test_control_flow(self):
        self.compare('let i = 0; while i < 3 { print("i=" + str(i)); i = i + 1; } fn add(a, b) { return a + b; } print(add(20, 22)); if add(1, 1) == 2 and not false { print("logic ok"); }')


if __name__ == "__main__":
    unittest.main()
