import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CC = os.environ.get("CC", "cc")
VM_SOURCE = os.path.join(ROOT, "native", "vm.c")
COMPILER = os.path.join(ROOT, "native", "compiler.py")
sys.path.insert(0, ROOT)
import sable


@unittest.skipUnless(shutil.which(CC), "no C compiler available")
class TestNativeVM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.vm = os.path.join(cls.directory.name, "sable-vm")
        subprocess.run([CC, "-O2", "-o", cls.vm, VM_SOURCE, "-lm"], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def compare(self, source):
        host_output = io.StringIO()
        with contextlib.redirect_stdout(host_output):
            sable.run_source(source)
        with tempfile.TemporaryDirectory() as tmp:
            source_path = os.path.join(tmp, "prog.sable")
            code_path = os.path.join(tmp, "prog.sasm")
            with open(source_path, "w") as handle:
                handle.write(source)
            compiled = subprocess.run(
                [sys.executable, COMPILER, source_path, "-o", code_path],
                capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([self.vm, code_path], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, host_output.getvalue())

    def test_arithmetic_and_variables(self):
        self.compare("print(1 + 2 * 3); let x = 5; x = x + 2; print(x);")

    def test_if_else(self):
        self.compare('if 3 > 2 { print("yes"); } else { print("no"); }')

    def test_while(self):
        self.compare("let i = 0; while i < 3 { print(i); i = i + 1; }")

    def test_strings_and_logic(self):
        self.compare('print("a" + "b"); if 1 < 2 and 3 > 2 { print("logic"); }')

    def test_unsupported_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_path = os.path.join(tmp, "prog.sable")
            code_path = os.path.join(tmp, "prog.sasm")
            with open(source_path, "w") as handle:
                handle.write("let xs = [1, 2];")
            result = subprocess.run(
                [sys.executable, COMPILER, source_path, "-o", code_path],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not support", result.stderr)


if __name__ == "__main__":
    unittest.main()
