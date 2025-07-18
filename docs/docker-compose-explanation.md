# Docker Compose Setup Explanation

## Overview

The `docker-compose.yml` file defines a multi-container application setup for the Log Analyzer Agent. It orchestrates three services that work together to provide a complete API-based log analysis system with authentication, database persistence, and caching capabilities.

## Services

### 1. PostgreSQL Database (`postgres`)

**Purpose**: Primary data storage for user authentication, session management, and analysis history.

**Configuration**:
- **Image**: `postgres:15` - Latest stable PostgreSQL version
- **Database Name**: `loganalyzer`
- **Credentials**: Username `loganalyzer`, password `password` (for development)
- **Port**: 5432 (standard PostgreSQL port)
- **Volume Mounts**:
  - `postgres_data:/var/lib/postgresql/data` - Persistent data storage
  - `./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql` - Database initialization script
- **Health Check**: Ensures database is ready before dependent services start

**Used For**:
- Storing user accounts and authentication data
- Session management for the API
- Saving analysis history and results
- Audit logs and usage tracking

### 2. Redis Cache (`redis`)

**Purpose**: In-memory data store for caching and session management.

**Configuration**:
- **Image**: `redis:7-alpine` - Lightweight Redis version
- **Port**: 6379 (standard Redis port)
- **Volume**: `redis_data:/data` - Persistent cache storage
- **Health Check**: Verifies Redis is responding to ping commands

**Used For**:
- Caching frequently accessed data
- Session storage for faster authentication
- Rate limiting and API throttling
- Temporary storage for analysis results
- Queue management for async tasks

### 3. Log Analyzer API (`log-analyzer-api`)

**Purpose**: Main application service providing the REST API for log analysis.

**Configuration**:
- **Build**: Uses local Dockerfile to build the application image
- **Dependencies**: Waits for PostgreSQL to be healthy before starting
- **Environment Variables**:
  - `DATABASE_URL`: Connection string to PostgreSQL
  - `GEMINI_API_KEY`: For Google's Gemini AI model (primary analysis)
  - `GROQ_API_KEY`: For Groq's API (orchestration model)
  - `TAVILY_API_KEY`: For web search capabilities
  - `BETTER_AUTH_SECRET`: Secret key for authentication
  - `BETTER_AUTH_URL`: Base URL for auth endpoints
- **Port**: 8000 (API server)
- **Volume**: `.:/app` - Mounts current directory for development
- **Command**: `python main.py --mode api` - Runs in API mode

**Features Provided**:
- REST API endpoints for log analysis
- User authentication and authorization
- WebSocket support for real-time streaming
- Integration with AI models for analysis
- Documentation search capabilities

## How It Works Together

1. **Startup Sequence**:
   - PostgreSQL starts first and runs initialization scripts
   - Redis starts independently
   - API service waits for PostgreSQL health check
   - All services become available

2. **Request Flow**:
   - Client sends log analysis request to API (port 8000)
   - API authenticates user via PostgreSQL
   - API checks Redis cache for similar analyses
   - API calls AI models (Gemini/Groq) for analysis
   - Results are cached in Redis and stored in PostgreSQL
   - Response sent back to client

3. **Data Persistence**:
   - PostgreSQL data persists in `postgres_data` volume
   - Redis cache persists in `redis_data` volume
   - Application code is mounted from host for development

## Development Benefits

1. **Isolated Environment**: Each service runs in its own container
2. **Easy Setup**: Single `docker-compose up` command starts everything
3. **Consistent Dependencies**: Same environment across all developers
4. **Hot Reloading**: Code changes reflect immediately (volume mount)
5. **Service Health Checks**: Ensures proper startup order

## Production Considerations

For production deployment, you would need to:
- Use environment-specific `.env` files
- Replace default passwords with secure ones
- Add SSL/TLS termination (nginx/traefik)
- Configure proper backup strategies
- Set up monitoring and logging
- Use managed database services
- Implement proper secret management

## Common Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Reset everything (including volumes)
docker-compose down -v

# Rebuild after code changes
docker-compose build

# Access PostgreSQL
docker-compose exec postgres psql -U loganalyzer -d loganalyzer

# Access Redis CLI
docker-compose exec redis redis-cli
```

## Environment Variables

The setup expects these environment variables (from `.env` file):
- `GEMINI_API_KEY`: Google AI API key
- `GROQ_API_KEY`: Groq API key
- `TAVILY_API_KEY`: Tavily search API key
- `BETTER_AUTH_SECRET`: Random secret for auth (generate with `openssl rand -base64 32`)

This architecture provides a scalable, maintainable foundation for the log analyzer API with proper separation of concerns and modern development practices.