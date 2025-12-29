import logging
from typing import List, Type

from google.genai import Client
from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field

from pydiscogs.utils.prompts import get_current_date, url_context_instructions

logger = logging.getLogger(__name__)


class UrlContextInput(BaseModel):
    urls: List[str] = Field(
        description="A list of URLs to use as context for the research."
    )
    query: str = Field(description="The research query or topic.")


class UrlContextTool(BaseTool):
    """A tool for performing research using a list of URLs as context."""

    name: str = "url_context"
    description: str = (
        "Performs web research on a given topic using the content of the provided URLs as context."
    )
    args_schema: Type[BaseModel] = UrlContextInput
    google_api_key: str
    google_llm_model: str

    def _run(self, urls: List[str], query: str):
        """Use the tool."""
        url_string = " ".join(urls)
        formatted_prompt = url_context_instructions.format(
            current_date=get_current_date(),
            research_topic=f"Compare the information from the following URLs: {url_string} to answer the question: {query}",
        )

        genai_client = Client(api_key=self.google_api_key)

        response = genai_client.models.generate_content(
            model=self.google_llm_model,
            contents=formatted_prompt,
            config={
                "tools": [{"url_context": {}}],
                "temperature": 0,
            },
        )
        logger.debug(f"url_context tool response: {response}")
        return response.text
