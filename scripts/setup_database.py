#!/usr/bin/env python3
"""Setup script to initialize the PostgreSQL database."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from log_analyzer_agent.services.auth_service import AuthService
from log_analyzer_agent.graph import create_enhanced_graph


async def setup_database():
    """Set up the database with all necessary tables."""
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)
    
    print(f"Setting up database: {db_url}")
    
    # Setup authentication tables
    print("Setting up authentication tables...")
    auth_service = AuthService(db_url)
    await auth_service.setup_tables()
    print("✓ Authentication tables created")
    
    # Setup LangGraph memory tables
    print("Setting up LangGraph memory tables...")
    try:
        graph, store, checkpointer = await create_enhanced_graph()
        print("✓ LangGraph memory tables created")
        
        # Clean up connections
        await store.close()
        await checkpointer.close()
        
    except Exception as e:
        print(f"Warning: LangGraph memory setup failed: {e}")
        print("This is expected if the database doesn't exist yet")
    
    print("\nDatabase setup completed successfully!")
    print("\nYou can now:")
    print("1. Start the API server: python main.py --mode api")
    print("2. Test the analysis: python main.py --mode test")


if __name__ == "__main__":
    asyncio.run(setup_database())