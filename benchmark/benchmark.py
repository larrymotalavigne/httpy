import asyncio
import time
import os
import sys
import subprocess
import statistics
import psutil
import requests
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import io
from contextlib import redirect_stdout

# Add the parent directory to the path so we can import httpy
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Function to generate a large payload
def generate_large_payload(size=100):
    """Generate a large JSON payload with the specified number of items."""
    return {f"key_{i}": f"value_{i}" * 10 for i in range(size)}

# Function to start the httpy server
def start_httpy_server(queue):
    from httpy import Response, get, post, route, run
    import os
    import json

    # Put the current process ID in the queue
    queue.put(os.getpid())

    # Simple endpoints
    @get("/")
    async def homepage(req):
        return Response.text("Hello, World!")

    @get("/json")
    async def json_endpoint(req):
        return Response.json({"message": "Hello, World!"})

    # Endpoints with larger payloads
    @get("/large-json")
    async def large_json_endpoint(req):
        return Response.json(generate_large_payload())

    # Endpoints with path parameters
    @get("/users/{user_id}")
    async def get_user(req):
        user_id = req.path_params['user_id']
        return Response.json({"user_id": user_id, "name": f"User {user_id}"})

    @get("/users/{user_id}/posts/{post_id}")
    async def get_user_post(req):
        user_id = req.path_params['user_id']
        post_id = req.path_params['post_id']
        return Response.json({"user_id": user_id, "post_id": post_id, "title": f"Post {post_id} by User {user_id}"})

    # POST endpoint that echoes the request body
    @post("/echo")
    async def echo(req):
        return Response.text(req.body)

    print("Starting httpy server on port 8000")
    asyncio.run(run(host="127.0.0.1", port=8000))

# Function to start the Starlette server
def start_starlette_server(queue):
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse, JSONResponse
    from starlette.routing import Route
    import uvicorn
    import os

    # Put the current process ID in the queue
    queue.put(os.getpid())

    # Simple endpoints
    async def homepage(request):
        return PlainTextResponse("Hello, World!")

    async def json_endpoint(request):
        return JSONResponse({"message": "Hello, World!"})

    # Endpoints with larger payloads
    async def large_json_endpoint(request):
        return JSONResponse(generate_large_payload())

    # Endpoints with path parameters
    async def get_user(request):
        user_id = request.path_params['user_id']
        return JSONResponse({"user_id": user_id, "name": f"User {user_id}"})

    async def get_user_post(request):
        user_id = request.path_params['user_id']
        post_id = request.path_params['post_id']
        return JSONResponse({"user_id": user_id, "post_id": post_id, "title": f"Post {post_id} by User {user_id}"})

    # POST endpoint that echoes the request body
    async def echo(request):
        body = await request.body()
        return PlainTextResponse(body.decode())

    routes = [
        Route("/", homepage),
        Route("/json", json_endpoint),
        Route("/large-json", large_json_endpoint),
        Route("/users/{user_id}", get_user),
        Route("/users/{user_id}/posts/{post_id}", get_user_post),
        Route("/echo", echo, methods=["POST"]),
    ]

    app = Starlette(routes=routes)
    print("Starting Starlette server on port 8001")
    # Set log_level to "error" to hide HTTP call logs
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

# Function to start the Flask server
def start_flask_server(queue):
    from flask import Flask, request, jsonify
    import os

    # Put the current process ID in the queue
    queue.put(os.getpid())

    app = Flask(__name__)

    # Simple endpoints
    @app.route("/")
    def homepage():
        return "Hello, World!"

    @app.route("/json")
    def json_endpoint():
        return jsonify({"message": "Hello, World!"})

    # Endpoints with larger payloads
    @app.route("/large-json")
    def large_json_endpoint():
        return jsonify(generate_large_payload())

    # Endpoints with path parameters
    @app.route("/users/<user_id>")
    def get_user(user_id):
        return jsonify({"user_id": user_id, "name": f"User {user_id}"})

    @app.route("/users/<user_id>/posts/<post_id>")
    def get_user_post(user_id, post_id):
        return jsonify({"user_id": user_id, "post_id": post_id, "title": f"Post {post_id} by User {user_id}"})

    # POST endpoint that echoes the request body
    @app.route("/echo", methods=["POST"])
    def echo():
        return request.data.decode()

    print("Starting Flask server on port 8002")
    # Disable Flask logs
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="127.0.0.1", port=8002, threaded=True, debug=False)

# Function to start the Tornado server
def start_tornado_server(queue):
    import tornado.ioloop
    import tornado.web
    import json
    import os

    # Put the current process ID in the queue
    queue.put(os.getpid())

    class HomeHandler(tornado.web.RequestHandler):
        def get(self):
            self.write("Hello, World!")

    class JsonHandler(tornado.web.RequestHandler):
        def get(self):
            self.write({"message": "Hello, World!"})

    class LargeJsonHandler(tornado.web.RequestHandler):
        def get(self):
            self.write(generate_large_payload())

    class UserHandler(tornado.web.RequestHandler):
        def get(self, user_id):
            self.write({"user_id": user_id, "name": f"User {user_id}"})

    class UserPostHandler(tornado.web.RequestHandler):
        def get(self, user_id, post_id):
            self.write({"user_id": user_id, "post_id": post_id, "title": f"Post {post_id} by User {user_id}"})

    class EchoHandler(tornado.web.RequestHandler):
        def post(self):
            self.write(self.request.body)

    app = tornado.web.Application([
        (r"/", HomeHandler),
        (r"/json", JsonHandler),
        (r"/large-json", LargeJsonHandler),
        (r"/users/([^/]+)", UserHandler),
        (r"/users/([^/]+)/posts/([^/]+)", UserPostHandler),
        (r"/echo", EchoHandler),
    ])

    print("Starting Tornado server on port 8003")
    # Disable Tornado logs
    import logging
    logging.getLogger("tornado.access").setLevel(logging.ERROR)
    logging.getLogger("tornado.application").setLevel(logging.ERROR)
    logging.getLogger("tornado.general").setLevel(logging.ERROR)
    # Explicitly specify host to avoid connection issues
    app.listen(8003, address="127.0.0.1")
    tornado.ioloop.IOLoop.current().start()

# Function to measure server performance
def measure_performance(server_name, port, pid, num_requests=1000, concurrency=10):
    base_url = f"http://127.0.0.1:{port}"

    # Define test scenarios
    scenarios = [
        # Simple GET requests
        {"name": "Simple Text", "method": "GET", "endpoint": "/", "data": None},
        {"name": "Simple JSON", "method": "GET", "endpoint": "/json", "data": None},

        # Requests with larger payloads
        {"name": "Large JSON", "method": "GET", "endpoint": "/large-json", "data": None},

        # Requests with path parameters
        {"name": "Path Params (1)", "method": "GET", "endpoint": "/users/123", "data": None},
        {"name": "Path Params (2)", "method": "GET", "endpoint": "/users/123/posts/456", "data": None},

        # POST request with payload
        {"name": "POST Echo", "method": "POST", "endpoint": "/echo", "data": "Hello, this is a test message that will be echoed back by the server."}
    ]

    results = {
        "server": server_name,
        "scenarios": {},
        "memory_usage": [],
        "cpu_usage": []
    }

    # Function to send a request and measure time
    def send_request(scenario):
        try:
            start_time = time.time()
            if scenario["method"] == "GET":
                response = requests.get(f"{base_url}{scenario['endpoint']}", timeout=2)
            elif scenario["method"] == "POST":
                response = requests.post(f"{base_url}{scenario['endpoint']}", data=scenario["data"], timeout=2)
            end_time = time.time()
            return end_time - start_time
        except (requests.exceptions.RequestException, ConnectionError) as e:
            print(f"  Error in {server_name} - {scenario['name']}: {str(e)}")
            return 10.0  # Return a high value to indicate failure

    # Get the server process by PID
    server_process = psutil.Process(pid)

    # Send requests and measure performance
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for scenario in scenarios:
            scenario_name = scenario["name"]
            print(f"Benchmarking {server_name} - {scenario_name}")

            # Initialize results for this scenario
            results["scenarios"][scenario_name] = {
                "request_times": []
            }

            # Warmup
            for _ in range(10):
                send_request(scenario)

            # Actual benchmark
            for i in range(0, num_requests, concurrency):
                batch_size = min(concurrency, num_requests - i)

                # Measure CPU and memory before batch
                cpu_percent = server_process.cpu_percent()
                memory_info = server_process.memory_info()

                # Send batch of requests
                batch_times = list(executor.map(
                    lambda _: send_request(scenario),
                    range(batch_size)
                ))

                results["scenarios"][scenario_name]["request_times"].extend(batch_times)
                results["cpu_usage"].append(cpu_percent)
                results["memory_usage"].append(memory_info.rss / (1024 * 1024))  # Convert to MB

    # Calculate statistics
    avg_memory = statistics.mean(results["memory_usage"])
    avg_cpu = statistics.mean(results["cpu_usage"])

    print(f"\n{server_name} Results:")

    # Print scenario-specific results
    for scenario_name, scenario_results in results["scenarios"].items():
        avg_time = statistics.mean(scenario_results["request_times"])
        p95_time = statistics.quantiles(scenario_results["request_times"], n=20)[18]  # 95th percentile

        print(f"  {scenario_name}:")
        print(f"    Average request time: {avg_time:.6f} seconds")
        print(f"    95th percentile request time: {p95_time:.6f} seconds")

        # Store the statistics for comparison
        results["scenarios"][scenario_name]["avg_time"] = avg_time
        results["scenarios"][scenario_name]["p95_time"] = p95_time

    print(f"Average memory usage: {avg_memory:.2f} MB")
    print(f"Average CPU usage: {avg_cpu:.2f}%")

    return {
        "server": server_name,
        "scenarios": results["scenarios"],
        "avg_memory": avg_memory,
        "avg_cpu": avg_cpu
    }

def main():
    # Check if required packages are installed
    missing_packages = []

    try:
        import starlette
        import uvicorn
    except ImportError:
        missing_packages.append("starlette uvicorn")

    try:
        import flask
    except ImportError:
        missing_packages.append("flask")

    try:
        import tornado
    except ImportError:
        missing_packages.append("tornado")

    try:
        import psutil
    except ImportError:
        missing_packages.append("psutil")

    if missing_packages:
        print("Some required packages are not installed. Please install them with:")
        for package in missing_packages:
            print(f"pip install {package}")
        return

    # Create queues for getting process IDs
    httpy_queue = multiprocessing.Queue()
    starlette_queue = multiprocessing.Queue()
    flask_queue = multiprocessing.Queue()
    tornado_queue = multiprocessing.Queue()

    # Create processes for each server
    httpy_process = multiprocessing.Process(target=start_httpy_server, args=(httpy_queue,))
    starlette_process = multiprocessing.Process(target=start_starlette_server, args=(starlette_queue,))
    flask_process = multiprocessing.Process(target=start_flask_server, args=(flask_queue,))
    tornado_process = multiprocessing.Process(target=start_tornado_server, args=(tornado_queue,))

    results = {}

    try:
        # Benchmark httpy
        print("\n=== Benchmarking httpy ===")
        httpy_process.start()
        time.sleep(2)  # Wait for server to start
        httpy_pid = httpy_queue.get(timeout=5)
        results["httpy"] = measure_performance("httpy", 8000, httpy_pid)
        httpy_process.terminate()
        httpy_process.join()

        # Benchmark Starlette
        print("\n=== Benchmarking Starlette ===")
        starlette_process.start()
        time.sleep(2)  # Wait for server to start
        starlette_pid = starlette_queue.get(timeout=5)
        results["starlette"] = measure_performance("starlette", 8001, starlette_pid)
        starlette_process.terminate()
        starlette_process.join()

        # Benchmark Flask
        print("\n=== Benchmarking Flask ===")
        flask_process.start()
        time.sleep(2)  # Wait for server to start
        flask_pid = flask_queue.get(timeout=5)
        results["flask"] = measure_performance("flask", 8002, flask_pid)
        flask_process.terminate()
        flask_process.join()

        # Benchmark Tornado
        print("\n=== Benchmarking Tornado ===")
        tornado_process.start()
        time.sleep(2)  # Wait for server to start
        tornado_pid = tornado_queue.get(timeout=5)
        results["tornado"] = measure_performance("tornado", 8003, tornado_pid)
        tornado_process.terminate()
        tornado_process.join()

        # Compare results
        print("\n=== Comparison Results ===")

        # Use httpy as the baseline for comparison
        baseline = results["httpy"]

        for server_name, server_results in results.items():
            if server_name == "httpy":
                continue

            print(f"\nhttpy vs {server_name.capitalize()} ratios:")
            print(f"Memory usage ratio: {baseline['avg_memory'] / server_results['avg_memory']:.2f}x")
            print(f"CPU usage ratio: {baseline['avg_cpu'] / server_results['avg_cpu']:.2f}x")

            print(f"\nRequest time ratios by scenario (httpy/{server_name.capitalize()}):")
            for scenario_name in baseline["scenarios"]:
                httpy_time = baseline["scenarios"][scenario_name]["avg_time"]
                other_time = server_results["scenarios"][scenario_name]["avg_time"]
                ratio = httpy_time / other_time
                print(f"  {scenario_name}: {ratio:.2f}x")

    finally:
        # Ensure all servers are stopped
        for process in [httpy_process, starlette_process, flask_process, tornado_process]:
            if process.is_alive():
                process.terminate()
                process.join()

if __name__ == "__main__":
    # Create output file path in the benchmark folder
    benchmark_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(benchmark_dir, "benchmark_results.txt")

    # Capture output to both console and file
    f = io.StringIO()
    with redirect_stdout(f):
        main()

    # Get the captured output
    output = f.getvalue()

    # Print the output to console
    print(output)

    # Write the output to the file
    with open(output_file, 'w') as file:
        file.write(output)

    print(f"\nBenchmark results written to: {output_file}")
