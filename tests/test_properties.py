import contextlib
import io
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sable


def run(source):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        sable.run_source(source)
    return output.getvalue()


class TestProperties(unittest.TestCase):
    def test_addition_commutes(self):
        rng = random.Random(1234)
        for _ in range(50):
            a = rng.randint(-100, 100)
            b = rng.randint(-100, 100)
            out = run(f"print({a} + {b} == {b} + {a});")
            self.assertEqual(out.strip(), "true")

    def test_multiplication_commutes(self):
        rng = random.Random(99)
        for _ in range(50):
            a = rng.randint(-50, 50)
            b = rng.randint(-50, 50)
            out = run(f"print({a} * {b} == {b} * {a});")
            self.assertEqual(out.strip(), "true")

    def test_list_push_pop_roundtrip(self):
        rng = random.Random(7)
        for _ in range(30):
            values = [rng.randint(-20, 20) for _ in range(rng.randint(0, 5))]
            value = rng.randint(-20, 20)
            source = f"let xs = {values}; push(xs, {value}); print(pop(xs)); print(len(xs));"
            out = run(source)
            self.assertEqual(out, f"{value}\n{len(values)}\n")

    def test_map_roundtrip(self):
        rng = random.Random(42)
        for _ in range(30):
            key = rng.randint(0, 20)
            value = rng.randint(-20, 20)
            source = f'let m = {{}}; m[{key}] = {value}; print(m[{key}]);'
            out = run(source)
            self.assertEqual(out, f"{value}\n")

    def test_string_concat_associative(self):
        rng = random.Random(5)
        alphabet = "abcdef"
        for _ in range(30):
            a = "".join(rng.choice(alphabet) for _ in range(4))
            b = "".join(rng.choice(alphabet) for _ in range(4))
            c = "".join(rng.choice(alphabet) for _ in range(4))
            source = f'print("{a}" + ("{b}" + "{c}") == ("{a}" + "{b}") + "{c}");'
            out = run(source)
            self.assertEqual(out.strip(), "true")


if __name__ == "__main__":
    unittest.main()
