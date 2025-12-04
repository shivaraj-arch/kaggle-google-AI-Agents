import os
from typing import Any, Dict
import sqlite3

import os
import asyncio
import pdb
import sys


from time import sleep
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError

from google.adk.agents import Agent, LlmAgent
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.models.google_llm import Gemini
from google.adk.sessions import DatabaseSessionService
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search

from google.adk.tools.tool_context import ToolContext
from google.genai import types
import logging
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import InMemoryRunner
from google.adk.plugins.logging_plugin import ( LoggingPlugin,)  
from google.genai import types
import asyncio


# Applies to all agent and model calls
class CountInvocationPlugin(BasePlugin):
    """A custom plugin that counts agent and tool invocations."""

    def __init__(self) -> None:
        """Initialize the plugin with counters."""
        super().__init__(name="count_invocation")
        self.agent_count: int = 0
        self.tool_count: int = 0
        self.llm_request_count: int = 0

    # Callback 1: Runs before an agent is called. You can add any custom logic here.
    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        """Count agent runs."""
        self.agent_count += 1
        logging.info(f"[Plugin] Agent run count: {self.agent_count}")

    # Callback 2: Runs before a model is called. You can add any custom logic here.
    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        """Count LLM requests."""
        self.llm_request_count += 1
        logging.info(f"[Plugin] LLM request count: {self.llm_request_count}")

class logConnector():
    def __init__(self):
        try:
            GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
            print("✅ Gemini API key setup complete.")
            
        except Exception as e:
            print(
                f"🔑 Authentication Error: Please make sure you have added 'GOOGLE_API_KEY' to your Kaggle secrets. Details: {e}"
            )

    def count_papers(self,papers: str):
        """
        This function counts the number of papers in a list of strings.
        Args:
          papers: A list of strings, where each string is a research paper.
        Returns:
          The number of papers in the list.
        """
        return len(papers)
    def prepare_logging_session(self):
        retry_config = types.HttpRetryOptions(
            attempts=5,  # Maximum retry attempts
            exp_base=7,  # Delay multiplier
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
        )
        google_search_agent = LlmAgent(
            name="google_search_agent",
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
            description="Searches for information using Google search",
            instruction="""Use the google_search tool to find information on the given topic. Return the raw search results.
            If the user asks for a list of papers, then give them the list of research papers you found and not the summary.""",
            tools=[google_search]
        )

# Root agent
        research_agent_with_plugin = LlmAgent(
            name="research_paper_finder_agent",
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
            instruction="""Your task is to find research papers and count them. 

            You MUST ALWAYS follow these steps:
            1) Find research papers on the user provided topic using the 'google_search_agent'. 
            2) Then, pass the papers to 'count_papers' tool to count the number of papers returned.
            3) Return both the list of research papers and the total number of papers.
            """,
            tools=[AgentTool(agent=google_search_agent), self.count_papers]
        )
        
        self.runner = InMemoryRunner(
        agent=research_agent_with_plugin,
        plugins=[
            LoggingPlugin()
        ],  # <---- 2. Add the plugin. Handles standard Observability logging across ALL agents
    )

        print("✅ Runner configured")
   
    async def logging_session(self,response=None):
        self.prepare_logging_session()
        print("🚀 Running agent with LoggingPlugin...")
        print("📊 Watch the comprehensive logging output below:\n")
        try:
            response = await self.runner.run_debug("Find recent papers on quantum computing")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Exception occurred: {e}")
        finally:
            if response is not None:
                #pdb.set_trace()
                #print(response)
                print(response[0].content.parts[0].text)
                await asyncio.sleep(1)



class AIConnector():
    def __init__(self):
        try:
            if os.path.exists("my_agent_data.db"):
                os.remove("my_agent_data.db")
            print("✅ ADK components imported successfully.")
            print("✅ Cleaned up old database files")
            self.APP_NAME = "default"  # Application
            self.USER_ID = "default"  # User
            self.SESSION = "default"  # Session

            self.MODEL_NAME = "gemini-2.5-flash-lite"
            self.persistent_args =[[["Hi, I am Sam! What is the capital of the United States?", "Hello! What is my name?"],"test-db-session-01"],[["What is the capital of India?", "Hello! What is my name?"],"test-db-session-01"],[["Hello! What is my name?"], "test-db-session-02"]]
            self.compaction_args = ["What is the latest news about AI in healthcare?","Are there any new developments in drug discovery?","Tell me more about the second development you found.","Who are the main companies involved in that?"]
            GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
            print("✅ Gemini API key setup complete.")
        except Exception as e:
            print(
                f"🔑 Authentication Error: Please make sure you have added 'GOOGLE_API_KEY' to your Kaggle secrets. Details: {e}"
            )


    # Define helper functions that will be reused throughout the notebook
    async def run_session(self,
        runner_instance: Runner,
        user_queries: list[str] | str = None,
        session_name: str = "default",
    ):
        print(f"\n ### Session: {session_name}")

        # Get app name from the Runner
        app_name = runner_instance.app_name

        # Attempt to create a new session or retrieve an existing one
        try:
            session = await self.session_service.create_session(
                app_name=app_name, user_id=self.USER_ID, session_id=session_name
            )
        except:
            session = await self.session_service.get_session(
                app_name=app_name, user_id=self.USER_ID, session_id=session_name
            )

        # Process queries if provided
        if user_queries:
            # Convert single query to list for uniform processing
            if type(user_queries) == str:
                user_queries = [user_queries]

            # Process each query in the list sequentially
            for query in user_queries:
                print(f"\nUser > {query}")

                # Convert the query string to the ADK Content format
                query = types.Content(role="user", parts=[types.Part(text=query)])

                # Stream the agent's response asynchronously
                async for event in runner_instance.run_async(
                    user_id=self.USER_ID, session_id=session.id, new_message=query
                ):
                    # Check if the event contains valid content
                    if event.content and event.content.parts:
                        # Filter out empty or "None" responses before printing
                        if (
                            event.content.parts[0].text != "None"
                            and event.content.parts[0].text
                        ):
                            print(f"{self.MODEL_NAME} > ", event.content.parts[0].text)
        else:
            print("No queries!")


    print("✅ Helper functions defined.")
    
    def prepare_stateful_session(self):
        self.retry_config = types.HttpRetryOptions(
            attempts=5,  # Maximum retry attempts
            exp_base=7,  # Delay multiplier
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
        )
        # Step 1: Create the LLM Agent
        self.root_agent = Agent(
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config),
            name="text_chat_bot",
            description="A text chatbot",  # Description of the agent's purpose
        )
        
        #logging


    def stateful_session(self):
        self.prepare_stateful_session()
        self.session_service = InMemorySessionService()
        # Step 3: Create the Runner
        self.runner = Runner(agent=self.root_agent, app_name=self.APP_NAME, session_service=self.session_service)
    
    async def stateful(self):
        self.stateful_session()
        await self.run_session(
            self.runner,
            [
                "Hi, I am Sam! What is the capital of United States?",
                "Hello! What is my name?",  # This time, the agent should remember!
            ],
            "stateful-agentic-session",
        )

# Step 1: Create the same agent (notice we use LlmAgent this time)
    def prepare_persistent_session(self):
        self.chatbot_agent = LlmAgent(
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config),
            name="text_chat_bot",
            description="A text chatbot with persistent memory",
        )
        self.db_url = "sqlite:///my_agent_data.db"  # Local SQLite file
        self.session_service = DatabaseSessionService(db_url=self.db_url)

    def persistent_session(self):
        self.prepare_persistent_session()
# Step 3: Create a new runner with persistent storage
        self.runner = Runner(agent=self.chatbot_agent, app_name=self.APP_NAME, session_service=self.session_service)

#asyncio.exceptions.CancelledError

    async def persistent_task(self,query_number,response=None):
        self.persistent_session()
        try:
            print(f"\nTask {query_number} started")
            response = await self.run_session(self.runner,self.persistent_args[query_number][0],self.persistent_args[query_number][1])
            await asyncio.sleep(1)
            print(f"Task {query_number} ended")
        except Exception as e:
            print(f"An error occurred in Task {query_number}: {e}")
            return
        finally:
            if response is not None:
                print(response[0].content.parts[0].text)
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(1)
                return


    async def persistent_serial_wrapper(self):
        # Use 'async with' to manage the group lifecycle
        try:
            for i in range(len(self.persistent_args)):
                await self.persistent_task(i)
            #async with asyncio.timeout(20):
            #await persistent()
            #task2_handle = tg.create_task(task_two())
        except Exception as e:
            # Handle potential exceptions raised by any task in the group (Python 3.11+)
            print(f"Caught exception: {e}")
        finally:
            await asyncio.sleep(1)

    async def delete_session(self):
        #async with asyncio.timeout(10):
        response = await self.session_service.delete_session("text_chat_bot","default","test-db-session-01")
        response = await self.session_service.delete_session("text_chat_bot","default","test-db-session-02")
        response = await self.session_service.delete_session("text_chat_bot","default","stateful-agentic-session")


    def check_data_in_db(self):
        with sqlite3.connect("my_agent_data.db") as connection:
            cursor = connection.cursor()
            result = cursor.execute(
                "select app_name, session_id, author, content from events"
            )
            print([_[0] for _ in result.description])
            for each in result.fetchall():
                print(each)


    def prepare_compact_session(self):
        self.chatbot_agent = LlmAgent(
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config),
            name="text_chat_bot",
            description="A text chatbot with persistent memory",
        )

# Re-define our app with Events Compaction enabled
        self.research_app_compacting = App(
            name="research_app_compacting",
            root_agent=self.chatbot_agent,
            # This is the new part!
            events_compaction_config=EventsCompactionConfig(
                compaction_interval=3,  # Trigger compaction every 3 invocations
                overlap_size=1,  # Keep 1 previous turn for context
            ),
        )

    def compact_session(self):
        self.prepare_compact_session()
        self.db_url = "sqlite:///my_agent_data.db"  # Local SQLite file
        self.session_service = DatabaseSessionService(db_url=self.db_url)
        # Create a new runner for our upgraded app
        self.research_runner_compacting = Runner( app=self.research_app_compacting, session_service=self.session_service)
        print("✅ Research App upgraded with Events Compaction!")

    async def compaction_task(self,query_number,response=None):
        self.compact_session()
        try:
            print(f"\nTask {query_number} started")
            response = await self.run_session(self.research_runner_compacting,self.compaction_args[query_number],"compaction_demo",)
            await asyncio.sleep(1)
            print(f"Task {query_number} ended")
        except Exception as e:
            print(f"An error occurred in Task {query_number}: {e}")
            return
        finally:
            if response is not None:
                print(response[0].content.parts[0].text)
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(1)
                return

    async def compaction_serial_wrapper(self):
        # Use 'async with' to manage the group lifecycle
        try:
            for task_num in range(len(self.compaction_args)):
            # Schedule tasks within the group
                await self.compaction_task(task_num)
            #async with asyncio.timeout(20):
            #await persistent()
            #task2_handle = tg.create_task(task_two())
        except Exception as e:
            # Handle potential exceptions raised by any task in the group (Python 3.11+)
            print(f"Caught exception: {e}")
        finally:
            await asyncio.sleep(1)

    async def final_s(self):
# Get the final session state
        try:
            final_session = await self.session_service.get_session(
                app_name=self.research_runner_compacting.app_name,
                user_id=self.USER_ID,
                session_id="compaction_demo",
            )
            if final_session:
                print("--- Searching for Compaction Summary Event ---")
                found_summary = False
                for event in final_session.events:
                    # Compaction events have a 'compaction' attribute
                    if event.actions and event.actions.compaction:
                        print("\n✅ SUCCESS! Found the Compaction Event:")
                        print(f"  Author: {event.author}")
                        print(f"\n Compacted information: {event}")
                        found_summary = True
                        break

                if not found_summary:
                    print(
                        "\n❌ No compaction event found. Try increasing the number of turns in the demo."
                    )
        except Exception as e:
            print(e,sys.exc_info())



# Define scope levels for state keys (following best practices)


# This demonstrates how tools can write to session state using tool_context.
# The 'user:' prefix indicates this is user-specific data.
    def save_userinfo(self,
        tool_context: ToolContext, user_name: str, country: str
    ) -> Dict[str, Any]:
        """
        Tool to record and save user name and country in session state.

        Args:
            user_name: The username to store in session state
            country: The name of the user's country
        """
        # Write to session state using the 'user:' prefix for user data
        USER_NAME_SCOPE_LEVELS = ("temp", "user", "app")
        tool_context.state["user:name"] = user_name
        tool_context.state["user:country"] = country

        return {"status": "success"}


# This demonstrates how tools can read from session state.
    def retrieve_userinfo(self,tool_context: ToolContext) -> Dict[str, Any]:
        """
        Tool to retrieve user name and country from session state.
        """
        # Read from session state
        user_name = tool_context.state.get("user:name", "Username not found")
        country = tool_context.state.get("user:country", "Country not found")

        return {"status": "success", "user_name": user_name, "country": country}
        print("✅ Tools created.")

    def prepare_session_state(self):
# Create an agent with session state tools
        self.root_agent = LlmAgent(
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config),
            name="text_chat_bot",
            description="""A text chatbot.
            Tools for managing user context:
            * To record username and country when provided use `save_userinfo` tool.
            * To fetch username and country when required use `retrieve_userinfo` tool.
            """,
            tools=[self.save_userinfo, self.retrieve_userinfo],  # Provide the tools to the agent
        )

# Set up session service and runner
        self.session_service = InMemorySessionService()
        self.runner = Runner(agent=self.root_agent, session_service=self.session_service, app_name="default")

        print("✅ Agent with session state tools initialized!")

    async def session_state_tools(self,response=None):
        try:
            self.prepare_session_state()
# Test conversation demonstrating session state
            response = await self.run_session(
                self.runner,
                [
                    "Hi there, how are you doing today? What is my name?",  # Agent shouldn't know the name yet
                    "My name is Sam. I'm from Poland.",  # Provide name - agent should save it
                    "What is my name? Which country am I from?",  # Agent should recall from session state
                ],
                "state-demo-session",
            )
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Exception occured in session_state_tools : {e}")
        finally:
            if response is not None:
                print(response[0].content.parts[x].text for x in range(len(response[0].content.parts)))
                await asyncio.sleep(1)

# Retrieve the session and inspect its state
        try:
            session = await self.session_service.get_session(
            app_name=self.APP_NAME, user_id=self.USER_ID, session_id="state-demo-session"
            )
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Exception occured in session_state_tools : {e}")
        finally:
            print("Session State Contents:")
            print(session.state)
            print("\n🔍 Notice the 'user:name' and 'user:country' keys storing our data!")
            await asyncio.sleep(1)


# Start a completely new session - the agent won't know our name
        try:
            response = await self.run_session(
                self.runner,
                ["Hi there, how are you doing today? What is my name?"],
                "new-isolated-session",
            )
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Exception occured in session_state_tools at new session : {e}")
        finally:
            if response:
                print(response[0].content.parts[0].text)
                await asyncio.sleep(1)

# Expected: The agent won't know the name because this is a different session

# Check the state of the new session
        try:
            session = await self.session_service.get_session(
            app_name=self.APP_NAME, user_id=self.USER_ID, session_id="new-isolated-session")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Exception occured in session_state_tools at new session : {e}")
        finally:
            print("New Session State:")
            print(session.state)
            await asyncio.sleep(1)

# Note: Depending on implementation, you might see shared state here.
# This is where the distinction between session-specific and user-specific state becomes important.
def compact_demo():
    try:
        aicon = AIConnector()
        asyncio.run(aicon.stateful())
        asyncio.run(aicon.persistent_serial_wrapper())
        asyncio.run(aicon.delete_session())
        aicon.check_data_in_db()
        asyncio.run(aicon.compaction_serial_wrapper())
        asyncio.run(aicon.final_s())
        asyncio.run(aicon.session_state_tools())
    except Exception as e:
        print(f"Exception in compact_demo : {e}")

def log_demo():
    try:
        logcon = logConnector()
        asyncio.run(logcon.logging_session())
    except Exception as e:
        print(f"Exception in log_demo : {e}")

if __name__=="__main__":
    try:
        #compact_demo()
        log_demo()
    except Exception as e:
        print(f"Exception in main : {e}")




# Clean up any existing database to start fresh (if Notebook is restarted)





