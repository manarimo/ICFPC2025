# Google Cloud Run Deployment Guide

This guide explains how to deploy the ICFP Wizardry application to Google Cloud Run.

## Prerequisites

1. **Google Cloud SDK**: Install and configure the `gcloud` CLI
   ```bash
   # Install Google Cloud SDK
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   
   # Login and set project
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Docker**: Ensure Docker is installed and running
   ```bash
   docker --version
   ```

3. **Enable Required APIs**:
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   ```

## Deployment Options

### Option 1: Using the Automated Script

1. Update the configuration in `deploy-to-cloud-run.sh`:
   ```bash
   PROJECT_ID="your-actual-project-id"
   SERVICE_NAME="icfp-wizardry"
   REGION="us-central1"  # or your preferred region
   ```

2. Run the deployment script:
   ```bash
   ./deploy-to-cloud-run.sh
   ```

### Option 2: Manual Deployment Steps

1. **Build the Docker image**:
   ```bash
   docker build -t icfp-wizardry .
   ```

2. **Tag for Google Container Registry**:
   ```bash
   docker tag icfp-wizardry gcr.io/YOUR_PROJECT_ID/icfp-wizardry
   ```

3. **Push to Container Registry**:
   ```bash
   docker push gcr.io/YOUR_PROJECT_ID/icfp-wizardry
   ```

4. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy icfp-wizardry \
     --image gcr.io/YOUR_PROJECT_ID/icfp-wizardry \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 3000 \
     --memory 1Gi \
     --cpu 1 \
     --concurrency 80 \
     --min-instances 0 \
     --max-instances 10 \
     --set-env-vars="NODE_ENV=production,NEXT_TELEMETRY_DISABLED=1"
   ```

### Option 3: Using Cloud Build (Recommended for CI/CD)

Create a `cloudbuild.yaml` file for automated builds:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/icfp-wizardry', '.']

  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/icfp-wizardry']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - run
      - deploy
      - icfp-wizardry
      - '--image=gcr.io/$PROJECT_ID/icfp-wizardry'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--port=3000'
      - '--memory=1Gi'
      - '--cpu=1'
      - '--concurrency=80'
      - '--min-instances=0'
      - '--max-instances=10'
      - '--set-env-vars=NODE_ENV=production,NEXT_TELEMETRY_DISABLED=1'

images:
  - 'gcr.io/$PROJECT_ID/icfp-wizardry'
```

Then trigger the build:
```bash
gcloud builds submit --config cloudbuild.yaml .
```

## Environment Variables

The application supports these environment variables:

- `NODE_ENV`: Set to `production` for production deployment
- `NEXT_TELEMETRY_DISABLED`: Set to `1` to disable Next.js telemetry
- `ICFP_API_BASE_URL`: API base URL (defaults to AWS endpoint)

## Resource Configuration

The current configuration allocates:
- **CPU**: 1 vCPU
- **Memory**: 1 GB
- **Concurrency**: 80 requests per instance
- **Scaling**: 0-10 instances (auto-scaling)

Adjust these values in the deployment command based on your needs:

```bash
--memory 512Mi        # For lighter workloads
--memory 2Gi          # For heavier workloads
--cpu 2               # For CPU-intensive workloads
--concurrency 1000    # For higher concurrency
--max-instances 100   # For higher traffic
```

## Custom Domain (Optional)

To use a custom domain:

1. **Map your domain**:
   ```bash
   gcloud run domain-mappings create \
     --service icfp-wizardry \
     --domain your-domain.com \
     --region us-central1
   ```

2. **Verify domain ownership** in Google Search Console

3. **Update DNS** with the provided CNAME records

## Monitoring and Logs

- **View logs**: `gcloud run services logs tail icfp-wizardry --region=us-central1`
- **Monitor**: Visit the Cloud Run console at https://console.cloud.google.com/run
- **Metrics**: Available in Cloud Monitoring

## Cost Optimization

Cloud Run charges for:
- **CPU**: While serving requests
- **Memory**: While serving requests  
- **Requests**: Per million requests
- **Networking**: Egress traffic

To optimize costs:
- Set appropriate min/max instances
- Use lower memory/CPU if sufficient
- Implement request batching where possible
- Consider regional placement near users

## Troubleshooting

### Common Issues:

1. **Build fails**: Check Docker build locally first
2. **Service unreachable**: Verify `--allow-unauthenticated` flag
3. **Cold starts**: Consider setting `--min-instances 1`
4. **Memory issues**: Increase `--memory` allocation
5. **Timeout errors**: Increase `--timeout` (max 3600s)

### Debug Commands:

```bash
# View service details
gcloud run services describe icfp-wizardry --region=us-central1

# View recent logs
gcloud run services logs tail icfp-wizardry --region=us-central1 --limit=50

# List all revisions
gcloud run revisions list --service=icfp-wizardry --region=us-central1
```

## Security Considerations

- The service is deployed with `--allow-unauthenticated` for public access
- Consider adding Cloud Armor for DDoS protection
- Use IAM roles for fine-grained access control
- Enable VPC connector for private resource access if needed

## Updates and Rollbacks

**Deploy new version**:
```bash
# Build new image and deploy
docker build -t icfp-wizardry .
docker tag icfp-wizardry gcr.io/YOUR_PROJECT_ID/icfp-wizardry:latest
docker push gcr.io/YOUR_PROJECT_ID/icfp-wizardry:latest
gcloud run deploy icfp-wizardry --image gcr.io/YOUR_PROJECT_ID/icfp-wizardry:latest --region=us-central1
```

**Rollback to previous version**:
```bash
# List revisions
gcloud run revisions list --service=icfp-wizardry --region=us-central1

# Route traffic to specific revision
gcloud run services update-traffic icfp-wizardry --to-revisions=REVISION_NAME=100 --region=us-central1
```