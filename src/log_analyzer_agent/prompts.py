"""Prompts for the Log Analyzer Agent.

This module defines the prompts used by different components of the log analyzer agent.
"""

from langchain_core.prompts import ChatPromptTemplate

# Main prompt for log analysis
MAIN_PROMPT = """You are an expert log analyzer assistant. Your task is to analyze the provided log content and:
1. Identify issues, errors, or anomalies in the logs
2. Provide accurate explanations of what the issues mean
3. Suggest solutions or next steps
4. Reference relevant documentation where applicable

{environment_context}

Always be specific in your analysis and recommendations. If you need additional information to provide a complete analysis, 
make sure to request it clearly with instructions on how the user can retrieve it.

Log Content:
{log_content}
"""

# Prompt for checking if analysis is complete or if more information is needed
ANALYSIS_CHECKER_PROMPT = """I'm reviewing the log analysis before finalizing it:

{analysis}

Given the log content and any available environment details, evaluate whether this analysis is:
1. Complete and accurate
2. Missing important details
3. Potentially misleading or incorrect

Specifically consider:
- Are all major errors/issues identified?
- Are the explanations technically accurate?
- Are the suggested solutions practical and appropriate?
- Would additional information from the user make the analysis significantly better?

If more information is needed, be specific about what should be requested and why.
"""

# Prompt for when the agent is requesting additional information
FOLLOWUP_PROMPT = """Based on the log analysis so far, I need to request some additional information to provide a more accurate and helpful analysis.

What I know so far:
{current_analysis}

What I need to know:
{follow_up_requests}

Please provide this information if available, and I'll continue with a more comprehensive analysis.
"""

# Prompt for searching documentation
DOCUMENTATION_SEARCH_PROMPT = """Based on the log analysis, I need to find relevant documentation to reference in my recommendations.

Key issues identified:
{issues}

Please formulate effective search queries to find documentation, guides, or forum posts that would help address these issues.
"""

# Main prompt template
main_prompt_template = ChatPromptTemplate.from_template(MAIN_PROMPT)

# Analysis checker prompt template
analysis_checker_template = ChatPromptTemplate.from_template(ANALYSIS_CHECKER_PROMPT)

# Follow-up prompt template
followup_template = ChatPromptTemplate.from_template(FOLLOWUP_PROMPT)

# Documentation search prompt template
documentation_search_template = ChatPromptTemplate.from_template(DOCUMENTATION_SEARCH_PROMPT)