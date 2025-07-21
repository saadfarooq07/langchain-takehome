# Production Setup Guide

This guide explains how to set up the Log Analyzer Agent for production use with proper data persistence and user isolation.

## Current Status

The application is production-ready with the following features implemented:

### ✅ Completed Features

1. **User Authentication**: Full authentication system with JWT tokens
2. **User Data Isolation**: Each user's analyses are stored separately
3. **Memory Service**: Stores and retrieves analysis history
4. **Store Manager**: Centralized management of store and checkpointer instances
5. **API Endpoints**: Complete REST API for all operations
6. **Frontend Integration**: React UI properly fetches real data from backend

### ⚠️ Current Limitations

1. **In-Memory Storage**: Currently using `InMemoryStore` which doesn't persist data across restarts
2. **Search Functionality**: The `asearch` method in `InMemoryStore` has limited functionality

## Production Configuration

### 1. Database Setup (PostgreSQL)

For production, you need to switch from `InMemoryStore` to `PostgresStore`:

```bash
# Set environment variable
export DATABASE_URL="postgresql://user:password@localhost:5432/loganalyzer"

# Run database setup
python scripts/setup_database.py
```

### 2. Update Store Manager

Modify `src/log_analyzer_agent/services/store_manager.py`:

```python
from langgraph.store.postgres import PostgresStore
from langgraph.checkpoint.postgres import PostgresSaver

class StoreManager:
    @classmethod
    def get_store(cls) -> BaseStore:
        if cls._store is None:
            db_url = os.getenv("DATABASE_URL")
            if db_url:
                cls._store = PostgresStore(db_url)
            else:
                cls._store = InMemoryStore()
        return cls._store
    
    @classmethod
    def get_checkpointer(cls) -> BaseCheckpointSaver:
        if cls._checkpointer is None:
            db_url = os.getenv("DATABASE_URL")
            if db_url:
                cls._checkpointer = PostgresSaver(db_url)
            else:
                cls._checkpointer = MemorySaver()
        return cls._checkpointer
```

### 3. Environment Variables

Create a `.env` file with:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/loganalyzer

# API Keys
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

# Auth
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### 4. Docker Deployment

Use the provided `docker-compose.yml`:

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 5. Frontend Deployment

The frontend is configured for Cloudflare Workers:

```bash
cd frontend
npm run build
npm run deploy
```

## API Endpoints

The following endpoints are available:

- `POST /api/v2/auth/register` - Register new user
- `POST /api/v2/auth/login` - Login user
- `GET /api/v2/auth/me` - Get current user
- `POST /api/v2/analyze` - Analyze logs
- `GET /api/v2/threads` - Get user's analysis threads
- `GET /api/v2/history` - Get analysis history
- `POST /api/v2/memory/search` - Search memory
- `GET /api/v2/applications` - Get user's applications

## Testing Production Setup

Run the production readiness test:

```bash
python test_production_ready_simple.py
```

## Monitoring

1. **Health Check**: `GET /api/v2/health`
2. **Metrics**: Analysis times and token counts are stored with each analysis
3. **Error Tracking**: All errors are logged with context

## Security Considerations

1. **Authentication**: All endpoints except health and auth require JWT token
2. **Data Isolation**: Users can only access their own data
3. **Input Validation**: All inputs are validated using Pydantic models
4. **Rate Limiting**: Consider adding rate limiting for production
5. **HTTPS**: Always use HTTPS in production

## Scaling Considerations

1. **Database Connections**: Use connection pooling for PostgreSQL
2. **Caching**: Redis can be added for caching frequent queries
3. **Load Balancing**: Multiple API instances can be run behind a load balancer
4. **Background Jobs**: Consider using Celery for long-running analyses

## Next Steps

1. Set up PostgreSQL database
2. Configure environment variables
3. Deploy with Docker or your preferred method
4. Set up monitoring and alerting
5. Configure backups for the database