# Database Deployment Strategy

This document outlines the database deployment strategy for Allogator using Supabase and Drizzle ORM.

## Architecture Overview

- **Frontend**: React app deployed to Cloudflare Workers
- **Backend API**: FastAPI deployed separately (handles auth and business logic)
- **Database**: Supabase (PostgreSQL) with Drizzle ORM
- **Authentication**: BetterAuth with Google OAuth

## Database Environments

### 1. Development

- Local Supabase instance or development project
- Migrations run locally with `bun run db:migrate`

### 2. Staging

- Dedicated Supabase project for staging
- URL: `https://your-staging-project.supabase.co`
- Migrations run via CI/CD pipeline

### 3. Production

- Dedicated Supabase project for production
- URL: `https://your-production-project.supabase.co`
- Migrations require approval and are run via CI/CD

## Migration Strategy

### Development Workflow

1. **Make schema changes** in `src/db/schema.ts`
2. **Generate migration**:
   ```bash
   cd /path/to/backend
   bun run db:generate
   ```
3. **Review migration** in `drizzle/` directory
4. **Apply migration**:
   ```bash
   bun run db:migrate
   ```

### Staging/Production Deployment

1. **Migrations are version controlled** in the `drizzle/` directory
2. **CI/CD pipeline runs migrations** before deploying new code
3. **Rollback strategy**: Keep previous migration scripts for reversal

## Supabase Configuration

### Row Level Security (RLS)

Enable RLS on all tables and configure policies:

```sql
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;

-- Example policy: Users can only see their own data
CREATE POLICY "Users can view own data" ON users
  FOR SELECT USING (auth.uid() = id);
```

### Edge Functions

If needed, deploy Supabase Edge Functions for:

- Complex authentication flows
- Data validation
- Background jobs

## Environment Variables

### Frontend (Cloudflare Workers)

- `VITE_SUPABASE_URL`: Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Public anon key

### Backend (API)

- `DATABASE_URL`: PostgreSQL connection string
- `SUPABASE_SERVICE_KEY`: Service role key (for admin operations)

## Security Best Practices

1. **Never expose service keys** in frontend code
2. **Use RLS policies** to secure data access
3. **Rotate keys regularly** in production
4. **Use different Supabase projects** for each environment
5. **Enable SSL/TLS** for all database connections

## Monitoring

1. **Database metrics** via Supabase dashboard
2. **Query performance** monitoring
3. **Error tracking** in application logs
4. **Backup verification** (automated by Supabase)

## Backup Strategy

Supabase provides:

- **Point-in-time recovery** (Pro plan)
- **Daily backups** (all plans)
- **Manual backup downloads** via dashboard

Additional recommendations:

- Schedule regular backup exports
- Test restore procedures quarterly
- Document recovery procedures

## Migration Checklist

Before deploying database changes:

- [ ] Schema changes tested locally
- [ ] Migration scripts reviewed
- [ ] RLS policies updated if needed
- [ ] Backup taken before migration
- [ ] Rollback plan documented
- [ ] Performance impact assessed
- [ ] Indexes optimized
- [ ] API compatibility verified

## Troubleshooting

### Common Issues

1. **Migration failures**
   - Check connection string
   - Verify permissions
   - Review migration SQL for errors

2. **Performance issues**
   - Check query plans
   - Add appropriate indexes
   - Review RLS policies

3. **Connection errors**
   - Verify environment variables
   - Check network connectivity
   - Confirm SSL settings

### Useful Commands

```bash
# Check migration status
bun run db:status

# Create manual backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Connect to database
psql $DATABASE_URL

# View current schema
\dt
\d+ table_name
```

## Integration with CI/CD

The GitHub Actions workflow should:

1. Run migrations in staging before deployment
2. Require manual approval for production migrations
3. Create backup before production migrations
4. Run smoke tests after migrations

See `.github/workflows/deploy.yml` for implementation details.
