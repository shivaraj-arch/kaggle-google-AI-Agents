import os
import pdb
#from kaggle_secrets import UserSecretsClient
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import load_memory, preload_memory
from google.genai import types
import asyncio

print("✅ ADK components imported successfully.")


class agent_memory():
    def __init__(self):
        try:
            GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
            print("✅ Gemini API key setup complete.")
        except Exception as e:
            print(
                f"🔑 Authentication Error: Please make sure you have added 'GOOGLE_API_KEY' to your Kaggle secrets. Details: {e}"
            )


        self.retry_config=types.HttpRetryOptions(
            attempts=5,  # Maximum retry attempts
            exp_base=7,  # Delay multiplier
            initial_delay=1, # Initial delay before first retry (in seconds)
            http_status_codes=[429, 500, 503, 504] # Retry on these HTTP errors
        )

    async def run_session(self,
        runner_instance: Runner, user_queries: list[str] | str, session_id: str = "default"
    ):
        """Helper function to run queries in a session and display responses."""
        print(f"\n### Session: {session_id}")

        # Create or retrieve session
        try:
            session = await self.session_service.create_session(
                app_name=self.APP_NAME, user_id=self.USER_ID, session_id=session_id
            )
        except:
            session = await self.session_service.get_session(
                app_name=self.APP_NAME, user_id=self.USER_ID, session_id=session_id
            )

        # Convert single query to list
        if isinstance(user_queries, str):
            user_queries = [user_queries]

        # Process each query
        for query in user_queries:
            print(f"\nUser > {query}")
            query_content = types.Content(role="user", parts=[types.Part(text=query)])

            # Stream agent response
            async for event in runner_instance.run_async(
                user_id=self.USER_ID, session_id=session.id, new_message=query_content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    text = event.content.parts[0].text
                    if text and text != "None":
                        print(f"Model: > {text}")


    print("✅ Helper functions defined.")
    
    def memory_svc(self):

        self.memory_service = (
        InMemoryMemoryService())  # ADK's built-in Memory Service for development and testing
        # Define constants used throughout the notebook
        self.APP_NAME = "MemoryDemoApp"
        self.USER_ID = "demo_user"

# Create agent
        self.user_agent = LlmAgent(
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config),
            name="MemoryDemoAgent",
            instruction="Answer user questions in simple words.",
        )

        print("✅ Agent created")
# Create Session Service
        self.session_service = InMemorySessionService()  # Handles conversations

# Create runner with BOTH services
        self.runner = Runner(
            agent=self.user_agent,
            app_name="MemoryDemoApp",
            session_service=self.session_service,
            memory_service=self.memory_service,  # Memory service is now available!
        )

        print("✅ Agent and Runner created with memory support!")

    async def interact(self):
        self.memory_svc()
# User tells agent about their favorite color
        await self.run_session(
            self.runner,
            "My favorite color is blue-green. Can you write a Haiku about it?",
            "conversation-01",  # Session ID
        )

        session = await self.session_service.get_session(
            app_name=self.APP_NAME, user_id=self.USER_ID, session_id="conversation-01"
        )

# Let's see what's in the session
        print("📝 Session contains:")
        for event in session.events:
            text = (
                event.content.parts[0].text[:60]
                if event.content and event.content.parts
                else "(empty)"
            )
            print(f"  {event.content.role}: {text}...")

# This is the key method!
        await self.memory_service.add_session_to_memory(session)

        print("✅ Session added to memory!")

# Create agent
        self.user_agent = LlmAgent(
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config),
            name="MemoryDemoAgent",
            instruction="Answer user questions in simple words. Use load_memory tool if you need to recall past conversations.",
            tools=[
                load_memory
            ],  # Agent now has access to Memory and can search it whenever it decides to!
        )

        print("✅ Agent with load_memory tool created.")

# Create a new runner with the updated agent
        self.runner = Runner(
            agent=self.user_agent,
            app_name=self.APP_NAME,
            session_service=self.session_service,
            memory_service=self.memory_service,
        )

        await self.run_session(self.runner, "What is my favorite color?", "color-test")

        await self.run_session(self.runner, "My birthday is on March 15th.", "birthday-session-01")

# Manually save the session to memory
        birthday_session = await self.session_service.get_session(
            app_name=self.APP_NAME, user_id=self.USER_ID, session_id="birthday-session-01"
        )

        await self.memory_service.add_session_to_memory(birthday_session)

        print("✅ Birthday session saved to memory!")

# Test retrieval in a NEW session
        await self.run_session(
            self.runner, "When is my birthday?", "birthday-session-02"  # Different session ID
        )

# Search for color preferences
        search_response = await self.memory_service.search_memory(
            app_name=self.APP_NAME, user_id=self.USER_ID, query="What is the user's favorite color?"
        )

        print("🔍 Search Results:")
        print(f"  Found {len(search_response.memories)} relevant memories")
        print()

        for memory in search_response.memories:
            if memory.content and memory.content.parts:
                text = memory.content.parts[0].text[:80]
                print(f"  [{memory.author}]: {text}...")


    async def auto_save_to_memory(self,callback_context):
        """Automatically save session to memory after each agent turn."""
        await callback_context._invocation_context.memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )


        print("✅ Callback created.")

    async def auto_memory(self):
# Agent with automatic memory saving
            auto_memory_agent = LlmAgent(
                model=Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config),
                name="AutoMemoryAgent",
                instruction="Answer user questions.",
                tools=[preload_memory],
                after_agent_callback=self.auto_save_to_memory,  # Saves after each turn!
            )

            print("✅ Agent created with automatic memory saving!")


# Create a runner for the auto-save agent
# This connects our automated agent to the session and memory services
            auto_runner = Runner(
                agent=auto_memory_agent,  # Use the agent with callback + preload_memory
                app_name=self.APP_NAME,
                session_service=self.session_service,  # Same services from Section 3
                memory_service=self.memory_service,
            )

            print("✅ Runner created.")


# Test 1: Tell the agent about a gift (first conversation)
# The callback will automatically save this to memory when the turn completes
            await self.run_session(
                auto_runner,
                "I gifted a new toy to my nephew on his 1st birthday!",
                "auto-save-test",
            )

# Test 2: Ask about the gift in a NEW session (second conversation)
# The agent should retrieve the memory using preload_memory and answer correctly
            await self.run_session(
                auto_runner,
                "What did I gift my nephew?",
                "auto-save-test-2",  # Different session ID - proves memory works across sessions!
            )


if __name__=="__main__":
    AM = agent_memory()
    asyncio.run(AM.interact())
    asyncio.run(AM.auto_memory())

