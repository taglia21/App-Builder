# Architecture - Ai Solution

## Overview

The architecture consists of a Next.js frontend, communicating with a FastAPI backend via REST API. The backend integrates with the n8n workflow automation platform and GitHub API. Data is stored in a PostgreSQL database, with Redis as a cache layer. Authentication is handled using JWT with refresh tokens, and OAuth providers for GitHub and Google. The application is hosted on AWS or Vercel, with CloudFront as a CDN and Route53 for DNS management. SSL certificates are managed using ACM.

## System Components

### Backend
- Framework: FastAPI
- Database: PostgreSQL
- Cache: Redis

### Frontend
- Framework: Next.js 14
- Language: TypeScript
- Styling: Tailwind CSS

## Authentication

{
  "method": "JWT with refresh tokens",
  "token_storage": "HttpOnly cookies",
  "oauth_providers": [
    "Google",
    "GitHub"
  ],
  "mfa_support": "TOTP",
  "session_duration": "15 min access, 7 day refresh"
}

## Deployment

{
  "provider": "AWS",
  "iac_tool": "Terraform",
  "resources": [
    {
      "name": "ECS Cluster",
      "purpose": "Container orchestration",
      "specs": "Fargate, auto-scaling 2-10 tasks"
    },
    {
      "name": "RDS PostgreSQL",
      "purpose": "Primary database",
      "specs": "db.t3.medium, Multi-AZ, 100GB"
    },
    {
      "name": "ElastiCache Redis",
      "purpose": "Caching and sessions",
      "specs": "cache.t3.micro, 1 node"
    },
    {
      "name": "S3",
      "purpose": "File storage",
      "specs": "Standard, versioning enabled"
    },
    {
      "name": "CloudFront",
      "purpose": "CDN for frontend",
      "specs": "Global distribution"
    },
    {
      "name": "ALB",
      "purpose": "Load balancing",
      "specs": "Application Load Balancer"
    }
  ]
}
