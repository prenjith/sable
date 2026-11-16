.PHONY: test fuzz verify

test:
	python3 -m unittest discover -s tests -v

fuzz:
	python3 tools/fuzz_parser.py

verify:
	python3 sable.py --verify examples/types.sable

playground:
	python3 tools/build_playground.py

CC ?= cc

native:
	$(CC) -O2 -o native/sable-vm native/vm.c -lm
