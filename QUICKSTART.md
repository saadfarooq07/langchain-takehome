# Quick Start Guide

## Prerequisites
- Python 3.11+
- Bun (for frontend)
- API Keys (Gemini, Groq, Tavily)

## Setup

### 1. Backend Setup
```bash
# Clone and install
git clone <repo>
cd langchain-takehome

# Install dependencies
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env and add your API keys:
# - GEMINI_API_KEY
# - GROQ_API_KEY  
# - TAVILY_API_KEY
```

### 2. Start Backend
```bash
# Simple - just run this:
uv run main.py

# Or with uv scripts:
uv run dev    # Development mode with auto-reload
uv run start  # Production mode
```

The backend API will start on http://localhost:8000

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies with Bun
bun install

# Start development server with Vite
bun run start
```

The frontend will start on http://localhost:3000 (using Vite for fast HMR)

## That's it!

- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Using the API

### Analyze Logs
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "log_content": "2024-01-01 ERROR Failed to connect to database",
    "environment_context": "Production PostgreSQL"
  }'
```

### With Docker
```bash
docker-compose up
```

This starts everything including PostgreSQL for persistence.