# httpy Benchmarks

This directory contains benchmarking tools for comparing httpy with other popular Python web frameworks.

## Frameworks Compared

The benchmark compares the following frameworks:

- httpy (this project)
- Starlette with Uvicorn
- Flask
- Tornado

## Requirements

To run the benchmarks, you need to install the following dependencies:

```bash
pip install flask tornado starlette uvicorn psutil
```

## Running the Benchmarks

To run the benchmarks, execute the following command from the project root:

```bash
python benchmark/benchmark.py
```

## What's Being Measured

The benchmark measures:

1. **Request processing time** for various scenarios:
   - Simple text responses
   - JSON responses
   - Large JSON payloads
   - Path parameters
   - POST requests with echo

2. **Memory usage** during request processing

3. **CPU usage** during request processing

## Performance Optimizations

The httpy framework has been optimized for performance in several key areas:

### Server Optimizations

1. **Efficient Buffer Management**:
   - Preallocated buffers with `bytearray` for better memory usage
   - Zero-copy operations using `memoryview`
   - Dynamic buffer resizing for handling large requests
   - Improved buffer reuse for persistent connections

2. **Request Parsing Improvements**:
   - Precompiled regex patterns for header and request line parsing
   - More efficient header parsing with optimized string operations
   - Latin1 encoding for header parsing (faster than UTF-8 for ASCII content)
   - Query parameter parsing and handling

3. **Connection Handling**:
   - Improved keep-alive connection handling
   - Better error handling with detailed error messages

### Request Optimizations

1. **JSON Parsing Caching**:
   - Cached JSON parsing to avoid re-parsing the same body multiple times
   - Added flags to track parsing state

2. **Query Parameter Support**:
   - Added support for URL query parameters
   - Convenience methods for accessing query and path parameters

### Response Optimizations

1. **Efficient Response Generation**:
   - BytesIO for efficient buffer concatenation
   - Cached encoded body to avoid re-encoding
   - Precomputed common headers and status lines as bytes
   - Optimized header writing with special cases for common headers

2. **JSON Improvements**:
   - Compact JSON encoding with `separators=(',', ':')`
   - Cached JSON serialization

3. **New Response Types**:
   - Added HTML response helper
   - Added redirect response helper

## Expected Performance Improvements

These optimizations are expected to improve httpy's performance in the following ways:

1. **Reduced Memory Usage**: Through more efficient buffer management and reuse
2. **Lower CPU Usage**: By avoiding redundant operations and using optimized methods
3. **Faster Request Processing**: Especially for JSON payloads and repeated requests
4. **Better Handling of Large Responses**: Through more efficient buffer concatenation
5. **Improved Connection Handling**: Better support for keep-alive connections

## Benchmark Results

The benchmark will output comparison results showing the relative performance of httpy compared to other frameworks.

Example output:

```
=== Comparison Results ===

httpy vs Starlette ratios:
Memory usage ratio: 0.75x
CPU usage ratio: 0.90x

Request time ratios by scenario (httpy/Starlette):
  Simple Text: 1.20x
  Simple JSON: 1.15x
  Large JSON: 1.05x
  Path Params (1): 1.10x
  Path Params (2): 1.08x
  POST Echo: 1.12x

httpy vs Flask ratios:
...

httpy vs Tornado ratios:
...
```

A ratio less than 1.0 means httpy is faster/more efficient, while a ratio greater than 1.0 means the other framework is faster/more efficient.
