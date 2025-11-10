from typing import Type

from google.genai import Client
from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field

# from pydiscogs.utils.gemini import get_citations, insert_citation_markers, resolve_urls
from pydiscogs.utils.prompts import get_current_date, web_searcher_instructions


class WebSearchInput(BaseModel):
    query: str = Field(description="The search query for the web research.")


class WebResearchTool(BaseTool):
    """A tool for performing web research using Google Search and Gemini."""

    name: str = "web_research"
    description: str = (
        "LangGraph node that performs web research using the native Google Search API tool. "
        "Executes a web search using the native Google Search API tool in combination with Gemini."
    )
    args_schema: Type[BaseModel] = WebSearchInput
    google_api_key: str
    google_llm_model: str

    def _run(self, query: str):
        """Use the tool."""
        # Configure
        formatted_prompt = web_searcher_instructions.format(
            current_date=get_current_date(),
            research_topic=query,
        )

        genai_client = Client(api_key=self.google_api_key)

        # Uses the google genai client as the langchain client doesn't return grounding metadata
        response = genai_client.models.generate_content(
            model=self.google_llm_model,
            contents=formatted_prompt,
            config={
                "tools": [{"google_search": {}}],
                "temperature": 0,
            },
        )
        # # resolve the urls to short urls for saving tokens and time
        # resolved_urls = resolve_urls(
        #     response.candidates[0].grounding_metadata.grounding_chunks, 1
        # )
        # # Gets the citations and adds them to the generated text
        # citations = get_citations(response, resolved_urls)
        # modified_text = insert_citation_markers(response.text, citations)
        # sources_gathered = [
        #     item for citation in citations for item in citation["segments"]
        # ]

        # data = {
        #     "sources_gathered": sources_gathered,
        #     "search_query": query,
        #     "web_research_result": modified_text,
        # }

        return response.text
