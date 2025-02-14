# ChatTNG Cloud Deployment Guide

This guide explains how to deploy ChatTNG to AWS cloud infrastructure.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI installed and configured
3. Node.js 18+ installed
4. Docker installed

## Initial Setup

1. Install AWS CDK CLI:
```bash
npm install -g aws-cdk
```

2. Configure AWS credentials:
```bash
aws configure
```

3. Install dependencies:
```bash
cd infrastructure/cdk
npm install
```

4. Bootstrap CDK (first time only):
```bash
cdk bootstrap
```

## Deployment Steps

1. Build and push Docker images:
```bash
# Build backend image
docker build -t chattng-backend ./backend
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker tag chattng-backend:latest $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/chattng-backend:latest
docker push $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/chattng-backend:latest
```

2. Deploy infrastructure:
```bash
cd infrastructure/cdk
cdk deploy
```

3. Update DNS records:
- Create A records for your domain pointing to the CloudFront distribution
- Create A records for your API subdomain pointing to the ALB

4. Build and deploy frontend:
```bash
cd frontend/chattng-web
npm run build
aws s3 sync dist/ s3://[WEBSITE_BUCKET_NAME]
```

## Environment Variables

After deployment, update `.env.production` with the values from CDK outputs:

- `DATABASE_URL`: Use the RDS endpoint
- `REDIS_URL`: Use the ElastiCache endpoint
- `API_URL`: Use your API domain
- `CLOUDFRONT_DOMAIN`: Use your CloudFront distribution domain

## Monitoring

- ECS Service metrics available in CloudWatch
- RDS metrics in CloudWatch
- ElastiCache metrics in CloudWatch
- Application logs in CloudWatch Logs

## Scaling

The infrastructure is set up to scale automatically:
- ECS Service scales based on CPU/Memory utilization
- RDS can be scaled vertically
- ElastiCache can be scaled horizontally

## Estimated Costs

Basic setup (per month):
- ECS Fargate: ~$40
- RDS t3.small: ~$30
- ElastiCache t3.micro: ~$15
- CloudFront: Pay per use
- S3: Pay per use
- Total: ~$85-100/month

## Security

- All services run in private subnets
- Access controlled via security groups
- Secrets managed via AWS Secrets Manager
- SSL/TLS encryption in transit
- Data encrypted at rest

## Backup and Recovery

- RDS automated backups enabled
- S3 versioning enabled
- Infrastructure as Code allows quick recovery

## Troubleshooting

1. Check CloudWatch Logs for application issues
2. Check ECS Service events for deployment issues
3. Verify security group rules if connectivity issues
4. Check CDK deployment logs for infrastructure issues

## Cleanup

To destroy the infrastructure:
```bash
cdk destroy
```

Note: This will delete all resources except:
- S3 buckets with content
- ECR repositories with images
- RDS snapshots 