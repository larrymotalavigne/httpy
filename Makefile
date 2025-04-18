.PHONY: test install benchmark clean

# Default target
all: test

# Install dependencies
install:
	pip install --upgrade pip
	pip install pytest
	pip install flask tornado starlette uvicorn psutil
	pip install -e .

# Run tests
test:
	pytest tests/

# Run benchmark
benchmark:
	python benchmark/benchmark.py

# Clean up
clean:
	rm -rf __pycache__
	rm -rf httpy/__pycache__
	rm -rf tests/__pycache__
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist