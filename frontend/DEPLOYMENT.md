# Cloudflare Workers Deployment Guide

This guide explains how to deploy the Allogator frontend to Cloudflare Workers with proper secrets management.

## Architecture Overview

- **Frontend**: React app on Cloudflare Workers (allogator.ai)
- **Backend**: Python/FastAPI on traditional cloud (api.allogator.ai)
- **Database**: Supabase PostgreSQL with Drizzle ORM
- **Auth**: BetterAuth with Google OAuth

## Prerequisites

1. Cloudflare account with Workers enabled
2. Domain `allogator.ai` configured in Cloudflare
3. Cloudflare API Token with Workers permissions
4. Google OAuth credentials

## Setup

### 1. Install Dependencies

```bash
bun install
```

### 2. Configure Environment Variables

Create environment-specific files:

- `.env.staging` - Staging environment variables
- `.env.production` - Production environment variables

Example:

```env
VITE_GOOGLE_CLIENT_ID=your-google-client-id
VITE_API_URL=https://api.allogator.ai/api/v2
VITE_AUTH_API_URL=https://api.allogator.ai
```

### 3. Configure Cloudflare Account

Update `wrangler.toml` with your Cloudflare account ID:

```toml
account_id = "your-cloudflare-account-id"
```

## Secrets Management

### Using the Script

Run the secrets management script:

```bash
bun run secrets:manage
```

This interactive script allows you to:

- Set individual secrets
- Set all secrets from `.env` files
- List current secrets

### Manual Secret Management

Set secrets manually using Wrangler:

```bash
# Staging
wrangler secret put VITE_GOOGLE_CLIENT_ID --env staging
wrangler secret put VITE_API_URL --env staging
wrangler secret put VITE_AUTH_API_URL --env staging

# Production
wrangler secret put VITE_GOOGLE_CLIENT_ID --env production
wrangler secret put VITE_API_URL --env production
wrangler secret put VITE_AUTH_API_URL --env production
```

## Deployment

### Local Development

```bash
bun run preview
```

This runs Wrangler in development mode locally.

### Deploy to Staging

```bash
bun run deploy:staging
```

### Deploy to Production

```bash
bun run deploy:production
```

## CI/CD with GitHub Actions

The repository includes a GitHub Actions workflow that automatically deploys:

- `staging` branch → staging.allogator.ai
- `main` branch → allogator.ai

### Required GitHub Secrets

Add these secrets to your GitHub repository:

1. **Cloudflare Secrets:**
   - `CLOUDFLARE_API_TOKEN` - Your Cloudflare API token
   - `CLOUDFLARE_ACCOUNT_ID` - Your Cloudflare account ID

2. **Staging Environment:**
   - `STAGING_GOOGLE_CLIENT_ID`
   - `STAGING_API_URL`
   - `STAGING_AUTH_API_URL`
   - `STAGING_SUPABASE_URL`
   - `STAGING_SUPABASE_ANON_KEY`

3. **Production Environment:**
   - `PRODUCTION_GOOGLE_CLIENT_ID`
   - `PRODUCTION_API_URL`
   - `PRODUCTION_AUTH_API_URL`
   - `PRODUCTION_SUPABASE_URL`
   - `PRODUCTION_SUPABASE_ANON_KEY`

## Domain Configuration

The application is configured to use:

- Production: `allogator.ai` and `www.allogator.ai`
- Staging: `staging.allogator.ai`

Ensure these domains are properly configured in your Cloudflare dashboard.

## Build Process

The build process:

1. Compiles TypeScript and JSX
2. Bundles with Vite
3. Optimizes for Cloudflare Workers
4. Splits vendor chunks for better caching

## Troubleshooting

### Build Errors

If you encounter build errors:

1. Ensure all dependencies are installed: `bun install`
2. Check TypeScript errors: `bun run typecheck`
3. Verify environment variables are set

### Deployment Errors

If deployment fails:

1. Verify Cloudflare API token has correct permissions
2. Check that the domain is active in Cloudflare
3. Ensure secrets are properly set: `wrangler secret list --env [environment]`

### Runtime Errors

Check logs using:

```bash
wrangler tail --env [environment]
```

## Security Best Practices

1. **Never commit secrets** - Use environment variables and Wrangler secrets
2. **Rotate API keys regularly** - Update both in Cloudflare and GitHub
3. **Use different credentials** for staging and production
4. **Enable 2FA** on Cloudflare and GitHub accounts
5. **Restrict API token permissions** to minimum required

## Performance Optimization

The setup includes:

- Code splitting for vendor libraries
- Minification and tree-shaking
- Cloudflare's global CDN
- Efficient static asset serving

## Monitoring

Monitor your Workers using:

- Cloudflare Dashboard Analytics
- Wrangler tail for real-time logs
- Custom error tracking (if implemented)
