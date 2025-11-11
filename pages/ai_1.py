import os
from dotenv import load_dotenv
from agents import Agent, Runner, trace

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

async def run_ai_tool():
    agent = Agent(
        name="assistant",
        model="gpt-5",  # Update with correct model
    )
    with trace("Simple Query"):
        result = await Runner.run(agent, "Hello, AI tool!")
        return result.final_output
