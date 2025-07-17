# Log Analyzer Agent Setup Guide

This guide will help you set up and run the Log Analyzer Agent with PostgreSQL memory backend.

## Prerequisites

- Python 3.9 or higher
- PostgreSQL 15 or higher
- Docker and Docker Compose (optional, for easy setup)

## Setup Instructions

### Option 1: Docker Compose (Recommended)

1. **Clone the repository and navigate to the project directory**
   ```bash
   git clone <repository-url>
   cd log-analyzer-agent
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   ```

3. **Edit the `.env` file** with your API keys:
   ```env
   # API Keys
   GEMINI_API_KEY=your_google_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   
   # Database (already configured for Docker)
   DATABASE_URL=postgresql://loganalyzer:password@postgres:5432/loganalyzer
   
   # Authentication
   BETTER_AUTH_SECRET=your_secret_key_here_min_32_chars
   BETTER_AUTH_URL=http://localhost:8000
   ```

4. **Start the services**
   ```bash
   docker-compose up -d
   ```

5. **Setup the database**
   ```bash
   docker-compose exec log-analyzer-api python scripts/setup_database.py
   ```

6. **Create a demo user**
   ```bash
   docker-compose exec log-analyzer-api python scripts/create_demo_user.py
   ```

7. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Option 2: Manual Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL**
   ```bash
   # Create database
   createdb loganalyzer
   
   # Create user
   psql -c "CREATE USER loganalyzer WITH PASSWORD 'password';"
   psql -c "GRANT ALL PRIVILEGES ON DATABASE loganalyzer TO loganalyzer;"
   ```

3. **Set environment variables**
   ```bash
   export DATABASE_URL=postgresql://loganalyzer:password@localhost:5432/loganalyzer
   export GEMINI_API_KEY=your_google_api_key_here
   export GROQ_API_KEY=your_groq_api_key_here
   export TAVILY_API_KEY=your_tavily_api_key_here
   export BETTER_AUTH_SECRET=your_secret_key_here_min_32_chars
   ```

4. **Setup the database**
   ```bash
   python scripts/setup_database.py
   ```

5. **Create a demo user**
   ```bash
   python scripts/create_demo_user.py
   ```

6. **Run the application**
   ```bash
   # Run API server
   python main.py --mode api
   
   # Or run test mode
   python main.py --mode test
   ```

## Usage

### API Endpoints

1. **Authentication**
   - `POST /api/v1/auth/register` - Register new user
   - `POST /api/v1/auth/login` - Login user
   - `POST /api/v1/auth/logout` - Logout user

2. **Log Analysis**
   - `POST /api/v1/analyze` - Analyze log content
   - `GET /api/v1/history` - Get analysis history
   - `GET /api/v1/applications` - Get user's applications

3. **Memory Management**
   - `POST /api/v1/memory/search` - Search memory
   - `GET /api/v1/user/preferences` - Get user preferences
   - `POST /api/v1/user/preferences` - Update user preferences

### Example Usage

1. **Register a user**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "password123",
       "full_name": "John Doe"
     }'
   ```

2. **Login**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "password123"
     }'
   ```

3. **Analyze logs**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/analyze" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "log_content": "2023-08-15T14:25:12.345Z ERROR [app.main] Database connection failed",
       "application_name": "MyApp",
       "environment_type": "production"
     }'
   ```

## Features

### Memory-Enhanced Analysis
- **Similar Issues**: Finds similar issues from your analysis history
- **Application Context**: Remembers application-specific patterns
- **User Preferences**: Personalizes analysis based on your preferences
- **Success Tracking**: Tracks which solutions work best

### Multi-User Support
- **Authentication**: Secure user registration and login
- **Data Isolation**: Each user's data is completely isolated
- **Session Management**: Secure session handling with JWT tokens

### Performance Optimizations
- **PostgreSQL Backend**: Efficient storage and retrieval
- **Memory Caching**: LangGraph's built-in memory system
- **Async Processing**: Non-blocking request handling

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL environment variable
   - Verify database user has proper permissions

2. **API Key Errors**
   - Ensure all API keys are set in environment variables
   - Check if keys are valid and have proper permissions

3. **Memory Setup Issues**
   - Run `python scripts/setup_database.py` to create tables
   - Check PostgreSQL logs for any errors

### Development Mode

For development, you can run the services individually:

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run setup
python scripts/setup_database.py

# Run in development mode
python main.py --mode api
```

### Testing

```bash
# Run basic test
python main.py --mode test

# Test with memory (requires database)
python main.py --mode test
```

## Architecture

The system is built with:

- **LangGraph**: Agent orchestration and memory management
- **PostgreSQL**: Persistent storage for checkpoints and memory
- **FastAPI**: REST API framework
- **Pydantic**: Data validation and serialization
- **JWT**: Authentication and session management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.