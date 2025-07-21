import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { createClient } from '@supabase/supabase-js';
import * as schema from './schema';
import * as dotenv from 'dotenv';

dotenv.config();

// Supabase client setup
const supabaseUrl = 'https://nrkwxhmvspmnjjwovzve.supabase.co';
const supabaseKey = process.env.SUPABASE_KEY!;

if (!supabaseKey) {
  throw new Error('SUPABASE_KEY is not set in environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseKey);

// Database connection for Drizzle
const connectionString = process.env.DATABASE_URL!;

if (!connectionString) {
  throw new Error('DATABASE_URL is not set in environment variables');
}

// For query purposes
const queryClient = postgres(connectionString);
export const db = drizzle(queryClient, { schema });

// For migrations
export const migrationClient = postgres(connectionString, { max: 1 });