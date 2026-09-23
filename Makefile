PYTHON ?= python

.PHONY: test inventory web mcp

test:
	$(PYTHON) -m unittest discover -s tests -v

inventory:
	$(PYTHON) -m iot_hardware_connectivity_bench inventory --pretty

web:
	$(PYTHON) -m iot_hardware_connectivity_bench web

mcp:
	$(PYTHON) -m iot_hardware_connectivity_bench mcp

