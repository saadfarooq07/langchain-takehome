import { db, supabase } from './db';
import { users, posts, comments } from './db/schema';
import { eq } from 'drizzle-orm';

async function examples() {
  // Example 1: Insert a user using Drizzle
  const newUser = await db.insert(users).values({
    email: 'john@example.com',
    name: 'John Doe',
  }).returning();
  
  console.log('New user created:', newUser);

  // Example 2: Query users using Drizzle
  const allUsers = await db.select().from(users);
  console.log('All users:', allUsers);

  // Example 3: Insert a post
  const newPost = await db.insert(posts).values({
    title: 'My First Post',
    content: 'This is the content of my first post',
    authorId: newUser[0].id,
    published: true,
  }).returning();

  console.log('New post created:', newPost);

  // Example 4: Query posts with author information
  const postsWithAuthors = await db
    .select({
      postId: posts.id,
      postTitle: posts.title,
      authorName: users.name,
      authorEmail: users.email,
    })
    .from(posts)
    .leftJoin(users, eq(posts.authorId, users.id));

  console.log('Posts with authors:', postsWithAuthors);

  // Example 5: Using Supabase client for real-time subscriptions
  const channel = supabase
    .channel('posts-changes')
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'posts',
      },
      (payload) => {
        console.log('Post change received:', payload);
      }
    )
    .subscribe();

  // Example 6: Update a post
  const updatedPost = await db
    .update(posts)
    .set({ title: 'Updated Title' })
    .where(eq(posts.id, newPost[0].id))
    .returning();

  console.log('Updated post:', updatedPost);

  // Example 7: Add a comment
  const newComment = await db.insert(comments).values({
    content: 'Great post!',
    postId: newPost[0].id,
    authorId: newUser[0].id,
  }).returning();

  console.log('New comment:', newComment);

  // Example 8: Complex query - Get posts with comment count
  const postsWithCommentCount = await db
    .select({
      post: posts,
      commentCount: db.$count(comments.id),
    })
    .from(posts)
    .leftJoin(comments, eq(posts.id, comments.postId))
    .groupBy(posts.id);

  console.log('Posts with comment count:', postsWithCommentCount);

  // Cleanup
  channel.unsubscribe();
}

// Run examples
examples().catch(console.error);