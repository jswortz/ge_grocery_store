FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY config/ config/
COPY src/ src/
COPY pyproject.toml .
COPY src/a2a_agent/requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV GOOGLE_CLOUD_PROJECT=wortz-project-352116
ENV GOOGLE_CLOUD_LOCATION=us-central1
ENV GOOGLE_GENAI_USE_VERTEXAI=TRUE
ENV RETAILER_NAME="ValueFresh Market"
ENV PROJECT_ID=wortz-project-352116
ENV ENGINE_ID=grocery-workshop-engine
ENV BQ_PROJECT=wortz-project-352116
ENV BQ_DATASET=ge_grocery_demo

EXPOSE 8080

CMD ["python", "-m", "src.a2a_agent.server"]
