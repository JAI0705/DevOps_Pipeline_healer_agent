# simple_agent.py

# Import libraries (like importing tools into your workshop)
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

# Load your API key from .env file
load_dotenv()

# Create an AI model instance
# Think of this as hiring a smart assistant
llm = ChatGroq(
    model="llama-3.3-70b-versatile",  # The AI model we're using
    temperature=0,  # 0 = very focused, 1 = creative
    api_key=os.getenv("GROQ_API_KEY")
)

# Test it out
def analyze_error(error_log):
    """
    This function takes an error message and asks the AI to explain it.

    Args:
        error_log (str): The error message from your build

    Returns:
        str: AI's explanation of the error
    """

    # Create a prompt (instructions for the AI)
    prompt = f"""
You are an expert programmer. Analyze this error and explain:
1. What went wrong?
2. What type of error is this? (syntax, import, logic, etc.)
3. Which file/line has the problem?

Error:
{error_log}

Respond in JSON format like this:
{{
    "summary": "brief explanation",
    "error_type": "the type",
    "location": "file and line"
}}
"""

    # Ask the AI
    response = llm.invoke(prompt)

    # Return the AI's answer
    return response.content


# Try it out!
if __name__ == "__main__":
    sample_error = """
Traceback (most recent call last):
  File "app.py", line 15, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
"""

    result = analyze_error(sample_error)
    print("AI Analysis:")
    print(result)
