# AWS production deployment blueprint

Recommended architecture:

CloudFront/WAF
    |
Application Load Balancer
    |
ECS/Fargate
  |        \
FastAPI   Celery worker
  |          |
RDS      ElastiCache Redis
  |
S3 private bucket

## S3

- Block all public access.
- Enable server-side encryption.
- Enable lifecycle expiration (for example 7 or 30 days, based on policy).
- Use presigned GET URLs for downloads.
- Store object keys scoped by authenticated user ID.

## Secrets

Use AWS Secrets Manager for:
- OPENAI_API_KEY
- ELEVENLABS_API_KEY
- identity-provider configuration

## Authentication

Use Amazon Cognito or an enterprise OIDC provider.
Validate issuer, audience, signature and token expiry in FastAPI.

## Malware scanning

Upload to a quarantine S3 prefix, scan with ClamAV/Lambda or a managed scanner,
then move only clean files to the private production prefix.

## Observability

Use CloudWatch/OpenTelemetry for:
- request latency
- error rate
- job duration
- provider failures
- queue depth
- artifact generation counts
- storage usage

Never log API keys, access tokens, raw voice data, or full user uploads.
