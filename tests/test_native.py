import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SABLEC = os.path.join(ROOT, "sablec.py")
CC = os.environ.get("CC", "cc")


@unittest.skipUnless(shutil.which(CC), "no C compiler available")
class TestNativeBackend(unittest.TestCase):
    def build_and_run(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            name = "prog"
            if os.name == "nt":
                name += ".exe"
            src = os.path.join(tmp, "prog.sable")
            exe = os.path.join(tmp, name)
            with open(src, "w") as handle:
                handle.write(source)
            result = subprocess.run(
                [sys.executable, SABLEC, src, "-o", exe],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            run = subprocess.run([exe], capture_output=True, text=True)
            return run.stdout, run.stderr

    def test_arithmetic(self):
        out, err = self.build_and_run("print(1 + 2 * 3); print((1 + 2) * 3);")
        self.assertEqual(out, "7\n9\n")

    def test_variables(self):
        out, err = self.build_and_run("let x = 5; x = x + 2; print(x);")
        self.assertEqual(out, "7\n")

    def test_if_else(self):
        out, err = self.build_and_run('if 3 > 2 { print("yes"); } else { print("no"); }')
        self.assertEqual(out, "yes\n")

    def test_while(self):
        out, err = self.build_and_run("let i = 0; while i < 3 { print(i); i = i + 1; }")
        self.assertEqual(out, "0\n1\n2\n")

    def test_for_range(self):
        out, err = self.build_and_run("for i in range(3) { print(i); }")
        self.assertEqual(out, "0\n1\n2\n")

    def test_functions(self):
        source = "fn fact(n) { if n <= 1 { return 1; } return n * fact(n - 1); } print(fact(5));"
        out, err = self.build_and_run(source)
        self.assertEqual(out, "120\n")

    def test_strings_and_conversions(self):
        out, err = self.build_and_run('print("a" + "b"); print(str(12), num("3.5"), len("hello"));')
        self.assertEqual(out, "ab\n12 3.5 5\n")

    def test_unsupported_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "prog.sable")
            exe = os.path.join(tmp, "prog")
            with open(src, "w") as handle:
                handle.write("let xs = [1, 2];")
            result = subprocess.run(
                [sys.executable, SABLEC, src, "-o", exe],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not support lists", result.stderr)

    def test_const_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "prog.sable")
            exe = os.path.join(tmp, "prog")
            with open(src, "w") as handle:
                handle.write("const x = 1; x = 2;")
            result = subprocess.run(
                [sys.executable, SABLEC, src, "-o", exe],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot assign to constant", result.stderr)


if __name__ == "__main__":
    unittest.main()
