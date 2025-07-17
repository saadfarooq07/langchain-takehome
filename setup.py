"""Setup script for log analyzer agent."""

from setuptools import setup, find_packages

setup(
    name="log-analyzer-agent",
    version="1.0.0",
    description="A LangGraph-based agent for analyzing logs with memory",
    author="Saad Farooq",
    author_email="saad.farooq07@gmail.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "langchain>=0.1.0",
        "langchain-core>=0.1.0",
        "langgraph>=0.0.20",
        "pydantic>=2.0.0",
        "langchain-google-genai>=0.0.5",
        "langchain-groq>=0.0.1",
        "langchain-community>=0.0.10",
        "aiohttp>=3.8.5",
        "tavily-python>=0.1.9",
        "python-dotenv>=1.0.0",
        "typing-extensions>=4.7.0",
        "psycopg[binary,pool]>=3.1.0",
        "asyncpg>=0.28.0",
        "langgraph-checkpoint-postgres>=0.0.10",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "bcrypt>=4.0.0",
        "python-multipart>=0.0.6",
        "pyjwt>=2.8.0",
        "email-validator>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "log-analyzer=main:main",
            "log-analyzer-api=main:run_api_server",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)