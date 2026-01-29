# agent_with_tools.py

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import os

load_dotenv()

# Define custom tools
@tool
def check_file_exists(filepath: str) -> str:
    """
    Check if a file exists in the current directory.

    Args:
        filepath: Path to the file to check

    Returns:
        String saying if file exists or not
    """
    if os.path.exists(filepath):
        return f"✓ File '{filepath}' exists"
    else:
        return f"✗ File '{filepath}' does not exist"


@tool
def read_file_content(filepath: str) -> str:
    """
    Read the contents of a file.

    Args:
        filepath: Path to the file to read

    Returns:
        The file contents or error message
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        return f"File content:\n{content}"
    except FileNotFoundError:
        return f"Error: File '{filepath}' not found"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(filepath: str, content: str) -> str:
    """
    Write content to a file.

    Args:
        filepath: Path where to write the file
        content: What to write in the file

    Returns:
        Success or error message
    """
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        return f"✓ Successfully wrote to '{filepath}'"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def list_files() -> str:
    """
    List all files in the current directory.

    Returns:
        A list of filenames
    """
    try:
        files = os.listdir('.')
        # Filter out hidden files and directories
        files = [f for f in files if os.path.isfile(f) and not f.startswith('.')]

        if files:
            return "Files in current directory:\n" + "\n".join(f"  - {f}" for f in files)
        else:
            return "No files found in current directory"
    except Exception as e:
        return f"Error listing files: {str(e)}"


# Create the AI model with system message built-in
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

# List of tools the agent can use
tools = [
    check_file_exists,
    read_file_content,
    write_file,
    list_files
]

# Create the agent - UPDATED VERSION
# No state_modifier parameter - we'll add system message differently
agent = create_react_agent(llm, tools)


def run_agent(user_input: str):
    """
    Run the agent with a user input.

    Args:
        user_input: What the user wants the agent to do

    Returns:
        The agent's response
    """
    print(f"\n{'='*60}")
    print(f"USER: {user_input}")
    print(f"{'='*60}\n")

    # Create messages with system message
    messages = [
        SystemMessage(content="You are a helpful file management assistant. "
                            "You can check, read, write, and list files. "
                            "Be concise in your responses."),
        ("user", user_input)
    ]

    # Run the agent
    result = agent.invoke({
        "messages": messages
    })

    # Get the final response
    final_message = result["messages"][-1]

    print(f"\n{'='*60}")
    print(f"AGENT: {final_message.content}")
    print(f"{'='*60}\n")

    return final_message.content


# Test it
if __name__ == "__main__":
    print("🤖 Agent with Tools - Interactive Demo")
    print("="*60)

    # Test 1: Create a test file
    print("\n📝 Test 1: Creating a test file...")
    run_agent("Create a file called 'test.txt' with the content 'Hello from the agent!'")

    # Test 2: Check if file exists
    print("\n🔍 Test 2: Checking if file exists...")
    run_agent("Does test.txt exist?")

    # Test 3: Read the file
    print("\n📖 Test 3: Reading the file...")
    run_agent("What's in test.txt?")

    # Test 4: List all files
    print("\n📋 Test 4: Listing all files...")
    run_agent("Show me all files in the current directory")

    # Test 5: Complex multi-step task
    print("\n🎯 Test 5: Complex task...")
    run_agent(
        "Create a file called 'report.txt', write 'Agent Test Report' in it, "
        "then tell me if it was created successfully"
    )

    print("\n✅ All tests complete!")
