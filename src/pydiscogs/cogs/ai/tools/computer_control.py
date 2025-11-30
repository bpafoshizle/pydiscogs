import asyncio
import json
import logging
import uuid
from typing import Type, Union

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools.computer_use.computer_use_toolset import ComputerUseToolset
from google.genai import types
from google.genai.errors import ClientError
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from xvfbwrapper import Xvfb

from .playwright_computer import PlaywrightComputer

logger = logging.getLogger(__name__)


class ComputerControlInput(BaseModel):
    query: Union[str, dict] = Field(
        description="The description of the task to accomplish on the computer."
    )


class ComputerControlTool(BaseTool):
    """A tool for controlling the computer using an agent built in Google ADK."""

    name: str = "computer_control"
    description: str = """
        Controls a computer (a browser at this point) by executing a command.
        This is a general purpose tool that can be used to look up
        information on the web by using a browser, especially if the url_context
        tool fails to handle a task.
        For any posts that need to be read on x.com, use this tool, as the url_context
        will not work on x.com.
        """
    args_schema: Type[BaseModel] = ComputerControlInput
    # google_api_key: str

    def _clean_query_payload(self, data):
        """Recursively remove image data from the query payload."""
        if isinstance(data, dict):
            if "image" in data and "data" in data["image"]:
                data["image"]["data"] = "[IMAGE_DATA_REMOVED]"
            for key, value in data.items():
                self._clean_query_payload(value)
        elif isinstance(data, list):
            for item in data:
                self._clean_query_payload(item)
        return data

    def _run(self, query: str, tool_call_id: str = None, **kwargs):
        """Use the tool."""
        # Handle case where LLM passes a nested dictionary (e.g. {'query': '...'})
        if isinstance(query, dict):
            query = query.get("query", str(query))
        logger.info(
            f"ComputerControlTool._run called with query type: {type(query)}, value: {query}"
        )
        with Xvfb():
            try:
                return asyncio.run(self.arun(query, tool_call_id=tool_call_id))
            except Exception as e:
                logger.debug("Exception caught in fallback", exc_info=True)
                logger.error(f"Error running ADK: {e}")
                return "Error controlling the computer."

    async def arun(self, query: str, tool_call_id: str = None, **kwargs):
        """Run the agent asynchronously."""
        # Handle case where LLM passes a nested dictionary (e.g. {'query': '...'})
        if isinstance(query, dict):
            query = query.get("query", str(query))

        # Try to parse query as JSON and clean it
        try:
            query_json = json.loads(query)
            query_json = self._clean_query_payload(query_json)
            query = json.dumps(query_json)
            logger.debug("Successfully cleaned query payload.")
        except (json.JSONDecodeError, TypeError) as e:
            # Not a JSON string or structure we can parse, proceed as is
            logger.debug(f"Could not parse query as JSON for cleaning: {e}")
            pass

        logger.info(f"ComputerControlTool.arun called with query length: {len(query)}")
        logger.debug(f"Query content (first 500 chars): {query[:500]}")
        # os.environ["GOOGLE_API_KEY"] = self.google_api_key
        agent = self.__get_agent()
        # Instantiate the InMemoryRunner
        runner = InMemoryRunner(app_name="agents", agent=agent)
        replies = []
        # Truncate query if it's too long to avoid token limit errors
        MAX_QUERY_LENGTH = 20000
        if len(query) > MAX_QUERY_LENGTH:
            logger.warning(
                f"Query too long ({len(query)} chars). Truncating to {MAX_QUERY_LENGTH} chars."
            )
            query = query[:MAX_QUERY_LENGTH] + "... [TRUNCATED]"

        content = types.Content(role="user", parts=[types.Part(text=query)])
        session_id = str(uuid.uuid4())

        try:
            await runner.session_service.create_session(
                app_name="agents", user_id="pydiscogs", session_id=session_id
            )
            async for event in runner.run_async(
                new_message=content, session_id=session_id, user_id="pydiscogs"
            ):
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    replies.append(event.content.parts[0].text)
        except ClientError as e:
            logger.error(f"ClientError in ComputerControlTool: {e}")
            return f"Error: The request was rejected by the AI model. Details: {e}"
        except Exception as e:
            logger.error(f"Unexpected error in ComputerControlTool: {e}", exc_info=True)
            return f"Error: An unexpected error occurred. Details: {e}"

        result = "\n".join(replies)
        if tool_call_id:
            return ToolMessage(content=result, tool_call_id=tool_call_id)
        return result

    def __get_agent(self):
        return Agent(
            model="gemini-2.5-computer-use-preview-10-2025",
            name="computer_agent",
            description=(
                "An agent that can operate a browser on a computer to finish user"
                " tasks."
            ),
            instruction="You are a computer use agent.",
            tools=[
                ComputerUseToolset(computer=PlaywrightComputer(screen_size=(1280, 936)))
            ],
        )
