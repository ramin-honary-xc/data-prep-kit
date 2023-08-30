# This Makefile runs MyPy type checking on any '*.py' file in this
# directory. It will also execute any file in this directory that
# matches the pattern 'test_*.py'. Make individual files, or make
# 'typecheck', 'tests', or 'all' (both) targets.

ifndef VIRTUAL_ENV
  include ../activate.mk
endif

PY_FILES = $(wildcard *.py)
SOURCE_FILES = $(filter-out test_%.py,$(PY_FILES))
TEST_FILES = $(filter test_%.py,$(PY_FILES))

# NOTE: that test files are defined as files which reside in the same
# directory as the module they are testing, and has the same name as
# the file that defines the module but with the string "test_"
# appended to the filname. This is how tests are selected.

.PHONY: tests all needs_check FORCE

all: typecheck tests

typecheck:
	mypy $(SOURCE_FILES)

tests: $(TEST_FILES)

# Rules for making individual files

$(SOURCE_FILES): FORCE
	mypy '$@';

test_%.py: %.py FORCE
	mypy '$@';
	python3 '$@';
