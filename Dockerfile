# Multi-stage build for Python distroless container
# Based on: https://alex-moss.medium.com/creating-an-up-to-date-python-distroless-container-image-e3da728d7a80

# Stage 1: Build dependencies
FROM python:3.9-slim as builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements to cache them in docker layer
COPY setup.py /app/
COPY README.md /app/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools && \
    pip wheel --no-cache-dir --wheel-dir /wheels -e .

# Stage 2: Copy application code
FROM python:3.9-slim as app-image
WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /wheels /wheels

# Copy application code
COPY httpy/ /app/httpy/
COPY examples/ /app/examples/

# Stage 3: Final distroless image
FROM gcr.io/distroless/python3-debian12
WORKDIR /app

# Copy wheels and application code from previous stages
COPY --from=builder /wheels /wheels
COPY --from=app-image /app /app

# Set Python path and expose port
ENV PYTHONPATH=/wheels:/app
EXPOSE 8080

# Set non-root user for better security (if supported by the distroless image)
# USER nonroot

# Run the application
CMD ["examples/server_example.py"]
