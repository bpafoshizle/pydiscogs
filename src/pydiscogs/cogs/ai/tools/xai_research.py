import logging
import re
from typing import Type, Any

from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field
from xai_sdk import AsyncClient
from xai_sdk.chat import user
from xai_sdk.tools import x_search, web_search

logger = logging.getLogger(__name__)


class XResearchInput(BaseModel):
    query: str = Field(
        description="The query, topic, or X post URL/ID to research or summarize using X (formerly Twitter) data."
    )


class XResearchTool(BaseTool):
    """A tool for performing research on X (formerly Twitter) using Xai's Grok via Native SDK.
    Can be used for summarizing specific posts (via URL/ID) or researching broader topics and trends.
    """

    name: str = "x_research"
    description: str = (
        "Researches topics, trends, or specific posts on X (formerly Twitter) using Grok. "
        "Useful for summaries, sentiment analysis, and real-time information gathering from X."
    )
    args_schema: Type[BaseModel] = XResearchInput
    xai_api_key: str

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        try:
            client = AsyncClient(api_key=self.xai_api_key)
            
            # Create a chat session with search tools enabled
            chat = client.chat.create(
                model="grok-4-1-fast",
                tools=[
                    x_search(),
                    web_search()
                ]
            )
            
            # Refine query for URLs to ensure research-mode is triggered
            refined_query = query
            if re.search(r'(twitter\.com|x\.com)/\w+/status/\d+', query):
                refined_query = f"Please research and provide a concise summary or TLDR of this X post: {query}"
            
            # Append query to state
            chat.append(user(refined_query))
            
            # Sample Grok for a response
            response = await chat.sample()
            logger.debug(f"XResearchTool sample response: {response}")

            # Based on logs, the response object HAS 'content' attribute directly exposed.
            # It seems the SDK flattens the final result into response.content for easy access.
            if hasattr(response, 'content') and response.content:
                logger.debug(f"XResearchTool found direct content: {response.content}")
                if isinstance(response.content, str):
                    return response.content
                # If it's a list or object, try to stringify or join it
                if hasattr(response.content, '__iter__'):
                     return "\n".join([str(c) for c in response.content])
                return str(response.content)

            # Fallback: check if we can access the raw proto or hidden fields if specific attributes are missing
            # The dir() showed _proto, maybe we need that if content is empty?
            # But normally .content should be populated if the status is completed.

            # Fallback to scanning chat history just in case
            logger.debug(f"XResearchTool chat history length: {len(chat.messages)}")
            if chat.messages:
                for i, msg in enumerate(reversed(chat.messages)):
                    logger.debug(f"XResearchTool msg {i} (reversed): {msg}")
                    if hasattr(msg, 'role') and msg.role == 2:
                        text = self._extract_text_from_msg(msg)
                        if text:
                            return text
            
            return "Error: Could not extract assistant response from Xai."

        except Exception as e:
            logger.error(f"Error in XResearchTool: {e}", exc_info=True)
            return f"Error performing X research: {str(e)}"

    def _extract_text_from_msg(self, msg: Any) -> str:
        """Helper to extract text from a Message object or similar."""
        if not hasattr(msg, 'content'):
            return ""
        
        content_objects = msg.content
        texts = []
        
        # content is often a RepeatedCompositeContainer (list-like) or just a string/attr
        if isinstance(content_objects, str):
             texts.append(content_objects)
        elif hasattr(content_objects, '__iter__'):
            for item in content_objects:
                if hasattr(item, 'text') and item.text:
                    texts.append(item.text)
                elif isinstance(item, str):
                    texts.append(item)
        elif hasattr(content_objects, 'text') and content_objects.text:
            texts.append(content_objects.text)
        else:
             texts.append(str(content_objects))
            
        return "\n".join(texts).strip()

    def _run(self, query: str) -> str:
        """Synchronous version not implemented - this tool requires async."""
        raise NotImplementedError("XResearchTool only supports async _arun")
