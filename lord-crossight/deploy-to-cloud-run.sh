#!/bin/bash

# Google Cloud Run Deployment Script for Lord-Crossight API

# Configuration - Update these values as needed
PROJECT_ID="manarimo-icfpc2025"
SERVICE_NAME="lord-crossight"
REGION="asia-northeast1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying Lord-Crossight API to Google Cloud Run"
echo "Project ID: $PROJECT_ID"
echo "Service Name: $SERVICE_NAME"
echo "Region: $REGION"

# Build and tag the Docker image
echo "📦 Building Docker image..."
docker build -t $SERVICE_NAME .

# Tag the image for Google Container Registry
echo "🏷️  Tagging image for GCR..."
docker tag $SERVICE_NAME $IMAGE_NAME

# Push the image to Google Container Registry
echo "☁️  Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars="PYTHONUNBUFFERED=1"

echo "✅ Deployment completed!"
echo "Your API should be available at:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)'