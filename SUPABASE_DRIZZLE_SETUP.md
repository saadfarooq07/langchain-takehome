# Supabase + Drizzle ORM Setup Guide (Bun)

## Setup Complete! 🎉

I've set up PostgreSQL with Supabase using Drizzle ORM with Bun. Here's what was created:

### Project Structure
```
├── src/
│   ├── db/
│   │   ├── schema.ts      # Database schema definitions
│   │   ├── index.ts       # Database connection and Supabase client
│   │   └── migrate.ts     # Migration runner
│   └── example.ts         # Usage examples
├── drizzle.config.ts      # Drizzle configuration
├── package.json           # Bun scripts and dependencies
└── .env.example          # Environment variables template
```

### Installation

```bash
# Install dependencies with Bun
bun install
```

### Next Steps

1. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add:
   - `SUPABASE_KEY`: Your Supabase anon key (from project settings)
   - `DATABASE_URL`: Your Supabase database URL

2. **Generate migrations**
   ```bash
   bun run db:generate
   ```

3. **Push schema to database**
   ```bash
   bun run db:push
   ```
   
   Or run migrations:
   ```bash
   bun run db:migrate
   ```

4. **Open Drizzle Studio** (database GUI)
   ```bash
   bun run db:studio
   ```

### Available Scripts

- `bun run db:generate` - Generate migration files from schema
- `bun run db:push` - Push schema directly to database (dev)
- `bun run db:migrate` - Run migrations
- `bun run db:studio` - Open Drizzle Studio GUI
- `bun run example` - Run the example file

### Schema Overview

The setup includes three tables:
- **users**: User accounts with email and name
- **posts**: Blog posts with title, content, and author
- **comments**: Comments on posts

### Usage Example

```typescript
import { db, supabase } from './db';
import { users, posts } from './db/schema';

// Insert a user
const newUser = await db.insert(users).values({
  email: 'user@example.com',
  name: 'John Doe',
}).returning();

// Query with joins
const postsWithAuthors = await db
  .select()
  .from(posts)
  .leftJoin(users, eq(posts.authorId, users.id));

// Use Supabase for real-time
const channel = supabase
  .channel('posts-changes')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'posts',
  }, (payload) => {
    console.log('Change:', payload);
  })
  .subscribe();
```

### Getting Your Supabase Credentials

1. Go to your Supabase project dashboard
2. Navigate to Settings → API
3. Copy:
   - `anon` public key → `SUPABASE_KEY`
   - Connection string → `DATABASE_URL`

### Tips

- Use `db:push` during development for quick schema updates
- Use migrations (`db:generate` + `db:migrate`) for production
- Drizzle Studio provides a nice GUI for viewing/editing data
- The example file (`src/example.ts`) shows common patterns

Need help? Check the [Drizzle docs](https://orm.drizzle.team/) or [Supabase docs](https://supabase.com/docs).