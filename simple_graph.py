# simple_graph.py

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from typing import TypedDict
from dotenv import load_dotenv
import os

load_dotenv()

# Step 1: Define the "State" (what information flows through the graph)
class AgentState(TypedDict):
    """
    This is like a form that gets passed from step to step.
    Each step can read and update the form.
    """
    error_log: str  # The error we're analyzing
    analysis: str   # AI's analysis of the error
    fix_suggestion: str  # AI's suggested fix
    current_step: str  # Track where we are


# Step 2: Create the AI model
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)


# Step 3: Define each step (node) in our workflow
def analyze_error_node(state: AgentState) -> AgentState:
    """
    First step: Analyze the error log
    """
    print("📊 Step 1: Analyzing error...")

    prompt = f"""
Analyze this error briefly (1 sentence):
{state['error_log']}
"""

    analysis = llm.invoke(prompt).content

    # Update the state and return it
    return {
        **state,  # Keep everything from before
        "analysis": analysis,  # Add the analysis
        "current_step": "analyzed"
    }


def suggest_fix_node(state: AgentState) -> AgentState:
    """
    Second step: Suggest a fix based on the analysis
    """
    print("🔧 Step 2: Suggesting fix...")

    prompt = f"""
Based on this analysis: {state['analysis']}

Suggest ONE simple fix (1-2 sentences):
"""

    fix = llm.invoke(prompt).content

    return {
        **state,
        "fix_suggestion": fix,
        "current_step": "fix_suggested"
    }


# Step 4: Build the graph (flowchart)
def create_simple_graph():
    """
    Create a workflow:
    Start → Analyze Error → Suggest Fix → End
    """

    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes (steps)
    workflow.add_node("analyze", analyze_error_node)
    workflow.add_node("suggest_fix", suggest_fix_node)

    # Define the flow
    workflow.set_entry_point("analyze")  # Start here
    workflow.add_edge("analyze", "suggest_fix")  # After analyze, go to suggest_fix
    workflow.add_edge("suggest_fix", END)  # After suggest_fix, we're done

    # Compile the graph
    return workflow.compile()


# Step 5: Run the graph
if __name__ == "__main__":
    # Create the graph
    graph = create_simple_graph()

    # Create initial state
    initial_state = {
        "error_log": """
Traceback (most recent call last):
  File "app.py", line 15
    print("Hello World"
SyntaxError: unexpected EOF while parsing
""",
        "analysis": "",
        "fix_suggestion": "",
        "current_step": "started"
    }

    # Run the graph
    print("🚀 Starting workflow...\n")
    final_state = graph.invoke(initial_state)

    # Print results
    print("\n" + "="*60)
    print("📋 RESULTS:")
    print("="*60)
    print(f"Analysis: {final_state['analysis']}")
    print(f"Fix: {final_state['fix_suggestion']}")
