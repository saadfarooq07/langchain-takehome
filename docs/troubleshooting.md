# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Log Analyzer Agent.

## API Key Issues

### Symptoms
- Error messages mentioning "API key not valid" or "Authentication failed"
- Models failing to load or initialize
- Empty responses from the agent

### Solutions

1. **Check Environment Variables**
   
   Make sure your API keys are properly set in the environment:
   
   ```bash
   # Verify keys are loaded
   python -c "import os; print('GEMINI_API_KEY:', bool(os.environ.get('GEMINI_API_KEY'))); print('GROQ_API_KEY:', bool(os.environ.get('GROQ_API_KEY'))); print('TAVILY_API_KEY:', bool(os.environ.get('TAVILY_API_KEY')))"
   ```

2. **Validate API Keys**
   
   Test each API key independently:
   
   ```bash
   python -c "from src.log_analyzer_agent.validation import APIKeyValidator; APIKeyValidator.validate_gemini_api_key('your_key_here')"
   
   python -c "from src.log_analyzer_agent.validation import APIKeyValidator; APIKeyValidator.validate_groq_api_key('your_key_here')"
   
   python -c "from src.log_analyzer_agent.validation import APIKeyValidator; APIKeyValidator.validate_tavily_api_key('your_key_here')"
   ```

3. **Regenerate API Keys**
   
   If validation fails, regenerate your keys from the provider websites:
   
   - Gemini: [Google AI Studio](https://ai.google.dev/)
   - Groq: [Groq Console](https://console.groq.com/)
   - Tavily: [Tavily Dashboard](https://tavily.com/)

4. **Check Quotas and Billing**
   
   Ensure you have sufficient quota or credits on each platform.

## Database Connection Issues (Memory Mode)

### Symptoms
- Error messages about database connections
- Memory features not working
- Errors when starting the agent in memory mode

### Solutions

1. **Check Connection String**
   
   Verify your database connection string format:
   
   ```
   postgresql://username:password@hostname:5432/dbname
   ```

2. **Test Database Connection**
   
   Run a simple connection test:
   
   ```bash
   python -c "import psycopg2; conn = psycopg2.connect('your_connection_string'); print('Connection successful!')"
   ```

3. **Initialize Database Tables**
   
   Make sure the database schema is set up:
   
   ```bash
   python scripts/setup_database.py
   ```

4. **Check PostgreSQL Service**
   
   Ensure PostgreSQL is running:
   
   ```bash
   # Linux/macOS
   systemctl status postgresql
   
   # Docker
   docker ps | grep postgres
   ```

5. **Network Issues**
   
   Check for network connectivity:
   
   ```bash
   # For local PostgreSQL
   telnet localhost 5432
   
   # For remote PostgreSQL
   telnet hostname 5432
   ```

## Log Processing Issues

### Symptoms
- Incomplete or incorrect analysis
- Errors during log parsing
- Empty results

### Solutions

1. **Check Log Format**
   
   Ensure your logs are in a readable text format:
   
   ```bash
   # View first few lines of log file
   head -n 20 your_logfile.log
   
   # Check for binary content
   file your_logfile.log
   ```

2. **Validate Log Content**
   
   Use the built-in validator:
   
   ```bash
   python -c "from src.log_analyzer_agent.validation import LogValidator; LogValidator.validate_log_content(open('your_logfile.log').read())"
   ```

3. **Preprocess Large Logs**
   
   For very large logs, consider preprocessing:
   
   ```bash
   # Extract the last 1000 lines
   tail -n 1000 large_logfile.log > recent_logs.log
   
   # Or extract specific time periods
   grep "2023-09-15" large_logfile.log > specific_date.log
   ```

4. **Check for Encoding Issues**
   
   Fix encoding problems:
   
   ```bash
   # Convert to UTF-8
   iconv -f ISO-8859-1 -t UTF-8 your_logfile.log > your_logfile_utf8.log
   ```

## Performance Issues

### Symptoms
- Agent running very slowly
- Timeouts during analysis
- High memory usage

### Solutions

1. **Use Minimal Mode**
   
   For faster processing with basic features:
   
   ```bash
   python main.py --mode minimal --log-file your_logfile.log
   ```

2. **Optimize Configuration**
   
   Create a streamlined configuration:
   
   ```python
   config = {
       "configurable": {
           "primary_model": "gemini:gemini-2.5-flash", 
           "max_tokens": 4096,  # Reduce from default
           "streaming": False,  # Disable streaming for batch processing
           "temperature": 0     # Deterministic output
       }
   }
   ```

3. **Chunk Large Logs**
   
   Process large logs in chunks:
   
   ```python
   from src.log_analyzer_agent import GraphFactory
   
   def analyze_in_chunks(log_file, chunk_size=5000):
       with open(log_file, 'r') as f:
           content = f.read()
       
       # Split into chunks (this is simplistic - consider timestamp-based chunking)
       lines = content.split('\n')
       chunks = ['\n'.join(lines[i:i+chunk_size]) for i in range(0, len(lines), chunk_size)]
       
       graph = GraphFactory.create_graph(mode="minimal")
       results = []
       
       for chunk in chunks:
           result = graph.invoke({"log_content": chunk})
           results.append(result["analysis_result"])
           
       # Combine results (implementation details omitted)
       return combine_results(results)
   ```

4. **Profile Resource Usage**
   
   Identify performance bottlenecks:
   
   ```bash
   # Install profiling tools
   pip install memory_profiler
   
   # Run with profiling
   python -m memory_profiler your_script.py
   ```

## Integration Issues

### Symptoms
- Errors when integrating with other systems
- Problems with API endpoints
- Authentication failures

### Solutions

1. **Check API Server**
   
   Verify the API server is running correctly:
   
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. **Test Authentication**
   
   Ensure authentication is working:
   
   ```bash
   # Register a test user
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com", "password":"securepassword", "full_name":"Test User"}'
     
   # Login to get token
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com", "password":"securepassword"}'
   ```

3. **Check CORS Settings**
   
   If integrating with frontend applications, verify CORS:
   
   ```python
   # In main.py or API initialization
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Restrict in production
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

4. **API Request Logging**
   
   Enable detailed logging for API requests:
   
   ```python
   import logging
   
   logging.basicConfig(level=logging.DEBUG)
   logging.getLogger("uvicorn").setLevel(logging.INFO)
   ```

## Docker Issues

### Symptoms
- Container startup failures
- Services not accessible
- Network connectivity problems

### Solutions

1. **Check Container Status**
   
   Verify containers are running:
   
   ```bash
   docker-compose ps
   ```

2. **View Container Logs**
   
   Check for errors in logs:
   
   ```bash
   docker-compose logs log-analyzer-api
   ```

3. **Network Configuration**
   
   Verify network settings:
   
   ```bash
   # List networks
   docker network ls
   
   # Inspect network
   docker network inspect log-analyzer_default
   ```

4. **Rebuild Containers**
   
   Rebuild with updated configuration:
   
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

5. **Volume Permissions**
   
   Fix permission issues:
   
   ```bash
   # Check volume permissions
   docker-compose exec log-analyzer-api ls -la /app/data
   
   # Fix if needed
   docker-compose exec log-analyzer-api chown -R nobody:nobody /app/data
   ```

## LangGraph Visualization Issues

### Symptoms
- Graph not appearing in LangGraph Dev
- Errors in LangGraph Dev console
- Unexpected graph behavior

### Solutions

1. **Check Graph Compatibility**
   
   Ensure graph is compatible with LangGraph Dev:
   
   ```python
   from src.log_analyzer_agent.studio_utils import clean_state_for_studio
   
   # Create graph with studio support
   graph = GraphFactory.create_graph(mode="interactive")
   graph = clean_state_for_studio(graph)
   ```

2. **Restart LangGraph Server**
   
   ```bash
   # Stop current server
   pkill -f "langgraph dev"
   
   # Start fresh
   langgraph dev
   ```

3. **Clear Browser Cache**
   
   Clear your browser cache or try an incognito window.

4. **Check Version Compatibility**
   
   Ensure you're using compatible versions:
   
   ```bash
   pip list | grep langgraph
   
   # If needed, install specific version
   pip install langgraph==0.0.15
   ```

## General Troubleshooting Steps

If you encounter issues not covered above:

1. **Check Logs**
   
   Look for error messages and exceptions:
   
   ```bash
   # Enable verbose logging
   python main.py --verbose
   ```

2. **Run Tests**
   
   Verify core functionality:
   
   ```bash
   python run_tests.py
   ```

3. **Update Dependencies**
   
   Ensure dependencies are up to date:
   
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **Debug Mode**
   
   Run with debug flags:
   
   ```bash
   # Set debug environment variable
   export LOG_ANALYZER_DEBUG=1
   
   # Run with debugging
   python main.py
   ```

5. **Get Support**
   
   If problems persist, gather information and seek help:
   
   ```bash
   # Gather system info
   python -c "import platform; print(platform.platform()); import sys; print(sys.version)"
   
   # List installed packages
   pip freeze > my_environment.txt
   ```

   Then open an issue in the project repository with these details.