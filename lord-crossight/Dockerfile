# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all Python files
COPY *.py ./
COPY *.json ./

# Create a non-root user for security
RUN addgroup --system --gid 1001 apiuser && \
    adduser --system --uid 1001 --gid 1001 apiuser

# Change ownership of the app directory
RUN chown -R apiuser:apiuser /app

# Switch to non-root user
USER apiuser

# Expose port 8000 (Cloud Run will map this to PORT env var)
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Start the server
CMD ["python", "server.py"]