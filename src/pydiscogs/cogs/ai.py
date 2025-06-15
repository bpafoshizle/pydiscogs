import logging
import os
import io
import contextlib
from httpx import ConnectError
from typing import List, Dict

import discord
from discord.ext import commands

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from google.genai import Client
from pydiscogs.utils.gemini import (
    get_citations,
    insert_citation_markers,
    resolve_urls,
)
from pydiscogs.utils.prompts import get_current_date, web_searcher_instructions

logger = logging.getLogger(__name__)


class AI(commands.Cog):
    def __init__(
        self,
        bot,
        ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT"),
        ollama_llm_model: str = os.getenv("OLLAMA_MODEL"),
        google_api_key: str = os.getenv("GOOGLE_API_KEY"),
        google_llm_model: str = os.getenv("GOOGLE_LLM_MODEL"),
        groq_api_key: str = os.getenv("GROQ_API_KEY"),
        groq_llm_model: str = os.getenv("GROQ_LLM_MODEL"),
        ai_system_prompt: str = os.getenv("AI_SYSTEM_PROMPT"),
    ):
        self.ai_handler = AIHandler(
            ollama_endpoint,
            ollama_llm_model,
            google_api_key,
            google_llm_model,
            groq_api_key,
            groq_llm_model,
            ai_system_prompt,
        )
        self.bot = bot

    @commands.slash_command()
    async def ai(self, ctx: discord.ApplicationContext, input: str):
        await ctx.defer()
        response = await self.ai_handler.call(input)
        await ctx.respond(response)

    @commands.message_command(name="AI Reply")
    async def ai_reply(self, ctx, message: discord.Message):
        modal = AIReplyModal(
            title="AI Reply",
            ai_handler=self.ai_handler,
            message_content=message.content,
        )
        await ctx.send_modal(modal)


class AIReplyModal(discord.ui.Modal):
    def __init__(self, *args, ai_handler, message_content, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ai_handler = ai_handler
        self.message_content = message_content
        self.add_item(
            discord.ui.InputText(label="Prompt", style=discord.InputTextStyle.long)
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        response = await self.ai_handler.call(
            self.children[0].value, self.message_content
        )
        await interaction.followup.send(response)


class AIHandler:
    def __init__(
        self,
        ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT"),
        ollama_llm_model: str = os.getenv("OLLAMA_LLM_MODEL"),
        google_api_key: str = os.getenv("GOOGLE_API_KEY"),
        google_llm_model: str = os.getenv("GOOGLE_LLM_MODEL"),
        groq_api_key: str = os.getenv("GROQ_API_KEY"),
        groq_llm_model: str = os.getenv("GROQ_LLM_MODEL"),
        ai_system_prompt: str = os.getenv("AI_SYSTEM_PROMPT"),
    ):
        if not any([ollama_endpoint, groq_api_key, google_api_key]):
            raise ValueError(
                "Must specify either ollama_endpoint, groq_api_key, or google_api_key"
            )

        self.ollama_endpoint = ollama_endpoint
        self.ollama_llm_model = ollama_llm_model
        self.groq_llm_model = groq_llm_model
        self.google_llm_model = google_llm_model
        self.google_api_key = google_api_key

        self.ai_system_prompt = ai_system_prompt

        self.tools = self.__get_tools()

        self.__setupLLMs()

    async def call(self, input: str, replied_to_message_content: str = ""):
        messages = {
            "messages": [
                HumanMessage(
                    content=f"previous message being replied to: {replied_to_message_content}"
                ),
                HumanMessage(content=input),
            ]
        }

        try:
            async for step in self.current_agent.astream(
                messages,
                stream_mode="values",
            ):
                response = step["messages"][-1]
                logger.debug("\n" + self.__get_pretty_print_response_string(response))
            return response.content
        except ConnectError as e:
            logger.error(f"Error caught: {e}.\nUsing fallback LLM.")
            try:
                self.__llm_cycle()
                # response = await self.current_agent.ainvoke(messages)
                logger.debug("AI response after fallback: ")
                async for step in self.current_agent.astream(
                    messages,
                    stream_mode="values",
                ):
                    response = step["messages"][-1]
                    logger.debug(
                        "\n" + self.__get_pretty_print_response_string(response)
                    )

                return response.content
            except Exception as e:
                logger.error(f"Unexpected error caught. Error message: {str(e)}")
                return "AI Error"

    def __setupLLMs(self):
        if self.ollama_endpoint:
            self.ollama_llm = self.__setupOllamaLLM(
                self.ollama_endpoint, self.ollama_llm_model
            )

        if self.groq_llm_model:
            self.groq_llm = self.__setupGroqLLM(self.groq_llm_model)

        if self.google_llm_model:
            self.google_llm = self.__setupGoogleLLM(self.google_llm_model)

        self.current_llm = self.google_llm
        self.fallback_llms = [self.ollama_llm, self.groq_llm]
        self.current_agent = create_react_agent(
            self.current_llm, self.tools, prompt=self.ai_system_prompt
        )

    def __setupGroqLLM(self, groq_llm_model: str):
        return ChatGroq(
            model=groq_llm_model,
            temperature=0.0,
            max_retries=2,
        )

    def __setupOllamaLLM(self, ollama_endpoint: str, ollama_llm_model: str):
        return ChatOllama(
            base_url=ollama_endpoint,
            model=ollama_llm_model,
            num_predict=330,
            temperature=0,
        )

    def __setupGoogleLLM(self, google_llm_model: str):
        logger.info("Using Google LLM model %s", google_llm_model)
        return ChatGoogleGenerativeAI(
            model=google_llm_model,
            temperature=0,
            max_retries=2,
        )

    def __llm_cycle(self):
        # Cycle through fallback_llms list, rotating the first element to the end.
        self.current_llm = self.fallback_llms[0]
        self.fallback_llms = self.fallback_llms[1:] + [self.fallback_llms[0]]
        self.current_agent = create_react_agent(
            self.current_llm, self.tools, prompt=self.ai_system_prompt
        )

    def __get_tools(self):
        from duckduckgo_search import DDGS
        from langchain_community.tools import BraveSearch
        from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
        from langchain_community.tools.playwright.utils import (
            create_async_playwright_browser,
        )

        @tool
        def web_search_image_ddg(query: str) -> List[Dict]:
            """Search the web for images using DuckDuckGo."""
            return DDGS().images(query, max_results=10)

        @tool
        def web_search_text_ddg(query: str) -> List[Dict]:
            """Search the web for text content using DuckDuckGo."""
            results = DDGS().text(query, max_results=10)
            logger.info(results)
            return results

        @tool
        def web_research(query: str):
            """LangGraph node that performs web research using the native Google Search API tool.

            Executes a web search using the native Google Search API tool in combination with Gemini 2.0 Flash.

            Args:
                state: Current graph state containing the search query and research loop count
                config: Configuration for the runnable, including search API settings

            Returns:
                Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
            """
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
            # resolve the urls to short urls for saving tokens and time
            resolved_urls = resolve_urls(
                response.candidates[0].grounding_metadata.grounding_chunks, 1
            )
            # Gets the citations and adds them to the generated text
            citations = get_citations(response, resolved_urls)
            modified_text = insert_citation_markers(response.text, citations)
            sources_gathered = [
                item for citation in citations for item in citation["segments"]
            ]

            data = {
                "sources_gathered": sources_gathered,
                "search_query": query,
                "web_research_result": [modified_text],
            }

            return data["web_research_result"]

        #brave_search = BraveSearch.from_api_key(os.getenv("BRAVE_SEARCH_API_KEY"))

        playwright_tools = PlayWrightBrowserToolkit.from_browser(
            async_browser=create_async_playwright_browser()
        ).get_tools()

        # return [web_search_text_ddg, web_search_image_ddg]
        return [web_research, *playwright_tools]

    def __get_pretty_print_response_string(self, response):
        pretty_output = ""
        # Capture pretty_print output:
        with io.StringIO() as buf, contextlib.redirect_stdout(buf):
            response.pretty_print()
            pretty_output = buf.getvalue()

        return pretty_output
