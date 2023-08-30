# file: activate.mk
# author: Ramin Honary
# date: 2023-08-30
# license: GPL3
#
# Ensure we are using the Python VIRTUAL_ENV in this current
# directory. This file is intended to be included (with the line of
# code "include ./activate.mk") at the top of a Makefile for a Python
# programming project:

export VIRTUAL_ENV := $(realpath $(or $(VIRTUAL_ENV),$(PWD)/env))

ifndef VIRTUAL_ENV
  ifneq (true,$(PYTHON_NO_VIRTUAL_ENV))
		COLON:=:
		define ERROR_MESSAGE =
			This makefile should be run in a Python virtual environment.
			You can run this Makefile with the arguments$(COLON)

					make PYTHON_NO_VIRTUAL_ENV=true

			to disable this check.

			To create a virtual environment$(COLON)

					python -m venv env

      To install the requirements for building this project
      run these commands once$(colon)

					. ./env/bin/activate;
          pip install -r ./requirements.txt;
		endef
    $(error $(ERROR_MESSAGE))
  endif
endif
export VIRTUAL_ENV

$(info Using virtual environment: $(VIRTUAL_ENV))

ifneq (FIND,$(findstring $(VIRTUAL_ENV)/bin,$(PATH)))
 export PATH := $(VIRTUAL_ENV)/bin:$(PATH)
endif
