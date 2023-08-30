# This Makefile runs MyPy type checking on any '*.py' file in all
# directories specified by the SRCDIRS variable. It will also execute
# any file in this directory that matches the pattern
# 'test_*.py'. Make individual files, or make 'typecheck', 'tests', or
# 'all' (both) targets.

ifndef VIRTUAL_ENV
  include activate.mk
endif

SRCDIRS := DataPrepKit

.PHONY: all FORCE

all: $(SRCDIRS)

$(SRCDIRS): FORCE
	$(MAKE) -C $@;

$(SRCDIRS)/%.py: FORCE
	$(MAKE) -C $(dir $@) $(notdir $@)
