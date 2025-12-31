FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Run the web server
CMD ["uvicorn", "ifc_validator.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
