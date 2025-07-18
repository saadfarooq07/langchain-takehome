# Setup Guide

This guide provides detailed instructions for setting up the Log Analyzer Agent in different environments.

## Basic Setup

### Prerequisites

- Python 3.9 or higher
- API keys for:
  - Gemini (for the primary analysis model)
  - Groq (for the orchestration model)
  - Tavily (for documentation search)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd log-analyzer-agent
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

## Docker Setup (for Memory mode)

For Memory mode with database support, Docker is recommended:

1. **Copy environment example**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your API keys and database settings**
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   DATABASE_URL=postgresql://username:password@postgres:5432/loganalyzer
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Setup database schema**
   ```bash
   docker-compose exec log-analyzer-api python scripts/setup_database.py
   ```

5. **Create demo user (optional)**
   ```bash
   docker-compose exec log-analyzer-api python scripts/create_demo_user.py
   ```

## Configuration Options

### API Keys

Required API keys:

- **GEMINI_API_KEY**: Get from [Google AI Studio](https://ai.google.dev/)
- **GROQ_API_KEY**: Get from [Groq](https://console.groq.com/)
- **TAVILY_API_KEY**: Get from [Tavily](https://tavily.com/)

### Database Setup (for Memory mode)

The Memory mode requires a PostgreSQL database. Configure it in your `.env` file:

```
DATABASE_URL=postgresql://username:password@localhost:5432/loganalyzer
```

You can run a PostgreSQL instance using Docker:

```bash
docker run --name postgres -e POSTGRES_PASSWORD=password -e POSTGRES_USER=username -e POSTGRES_DB=loganalyzer -p 5432:5432 -d postgres
```

Then initialize the database:

```bash
python scripts/setup_database.py
```

## Verification

To verify your installation:

1. **Run the minimal version**
   ```bash
   python main.py --mode minimal --log-file examples/sample.log
   ```

2. **Run the test suite**
   ```bash
   python run_tests.py
   ```

If all tests pass, your installation is ready to use.

## Troubleshooting Setup Issues

### API Key Issues

If you encounter errors related to API keys:

1. Verify the keys are correctly set in your `.env` file
2. Ensure you have sufficient quota/credits on the respective platforms
3. Try running `python -c "import os; print(os.environ.get('GEMINI_API_KEY'))"` to check if the key is properly loaded

### Database Connection Issues

For Memory mode database problems:

1. Ensure PostgreSQL is running and accessible
2. Check connection string format: `postgresql://username:password@hostname:5432/dbname`
3. Verify network connectivity between your application and the database
4. Look for database logs for any authentication or connection errors

### Docker Issues

If Docker setup isn't working:

1. Ensure Docker and Docker Compose are properly installed
2. Check if containers are running with `docker-compose ps`
3. View logs with `docker-compose logs`
4. Verify port mappings and network configurations in `docker-compose.yml`