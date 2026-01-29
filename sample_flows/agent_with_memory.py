# agent_with_memory.py

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import os

load_dotenv()

# Create the AI model
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

# Simple conversation memory using a list
class SimpleMemory:
    """
    A simple memory system that stores conversation history.
    Think of this as a notebook where we write down everything.
    """
    def __init__(self):
        self.messages = []  # List to store all messages

    def add_user_message(self, message: str):
        """Add what the user said"""
        self.messages.append(HumanMessage(content=message))

    def add_ai_message(self, message: str):
        """Add what the AI said"""
        self.messages.append(AIMessage(content=message))

    def get_messages(self):
        """Get all messages in the conversation"""
        return self.messages

    def clear(self):
        """Forget everything"""
        self.messages = []


# Create memory instance
memory = SimpleMemory()

# Create a prompt that includes conversation history
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant that remembers our conversation."),
    MessagesPlaceholder(variable_name="history"),  # This is where past messages go
    ("human", "{input}")  # Current user message
])

# Create a chain: prompt + llm
chain = prompt | llm


def chat(user_input: str) -> str:
    """
    Send a message and get a response (with memory!)

    Args:
        user_input: What the user wants to say

    Returns:
        The AI's response
    """
    # Get conversation history
    history = memory.get_messages()

    # Ask the AI (with full history)
    response = chain.invoke({
        "history": history,
        "input": user_input
    })

    # Save both messages to memory
    memory.add_user_message(user_input)
    memory.add_ai_message(response.content)

    return response.content


# Test it
if __name__ == "__main__":
    print("🤖 Agent with Memory - Testing")
    print("=" * 60)
    print("(Type 'quit' to exit, 'clear' to reset memory)\n")

    while True:
        # Get user input
        user_input = input("You: ")

        # Check for commands
        if user_input.lower() == 'quit':
            print("Goodbye! 👋")
            break
        elif user_input.lower() == 'clear':
            memory.clear()
            print("🧹 Memory cleared!\n")
            continue

        # Get AI response
        response = chat(user_input)
        print(f"Agent: {response}\n")
