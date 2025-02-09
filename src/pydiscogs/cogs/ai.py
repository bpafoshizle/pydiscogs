import logging
import os
from httpx import ConnectError
from typing import List, Dict

import discord
from discord.ext import commands

from duckduckgo_search import DDGS

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool


logger = logging.getLogger(__name__)

class AI(commands.Cog):
    def __init__(
        self,
        bot,
        ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT"),
        google_api_key: str = os.getenv("GOOGLE_API_KEY"),
        google_llm_model: str = os.getenv("GOOGLE_LLM_MODEL"),
        groq_api_key: str = os.getenv("GROQ_API_KEY"),
        groq_llm_model: str = os.getenv("GROQ_LLM_MODEL"),
        ai_system_prompt: str = os.getenv("AI_SYSTEM_PROMPT")
    ):
        self.ai_handler = AIHandler(
            ollama_endpoint, 
            google_api_key, google_llm_model, 
            groq_api_key, groq_llm_model, 
            ai_system_prompt
        )
        self.bot = bot
    
    @commands.slash_command()
    async def ai(self, ctx: discord.ApplicationContext, input: str):
        await ctx.defer()
        response = await self.ai_handler.call(input)
        await ctx.respond(response)

    @commands.message_command(name="AI Reply")
    async def ai_reply(self, ctx, message: discord.Message):
        modal = AIReplyModal(title="AI Reply", ai_handler=self.ai_handler, message_content=message.content)
        await ctx.send_modal(modal)
    

class AIReplyModal(discord.ui.Modal):
    def __init__(self, *args, ai_handler, message_content, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ai_handler = ai_handler
        self.message_content = message_content
        self.add_item(discord.ui.InputText(label="Prompt", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        response = await self.ai_handler.call(self.children[0].value, self.message_content)
        await interaction.followup.send(response)

class AIHandler():
    def __init__(self,
        ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT"),
        google_api_key: str = os.getenv("GOOGLE_API_KEY"),
        google_llm_model: str = os.getenv("GOOGLE_LLM_MODEL"),
        groq_api_key: str = os.getenv("GROQ_API_KEY"),
        groq_llm_model: str = os.getenv("GROQ_LLM_MODEL"),
        ai_system_prompt: str = os.getenv("AI_SYSTEM_PROMPT")
    ):
        if not any([ollama_endpoint, groq_api_key, google_api_key]):
            raise ValueError(
                "Must specify either ollama_endpoint, groq_api_key, or google_api_key"
            )
        
        self.ollama_endpoint = ollama_endpoint
        self.groq_llm_model = groq_llm_model
        self.google_llm_model = google_llm_model

        self.ai_system_prompt = ai_system_prompt

        self.tools = self.__get_tools()
        
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    ai_system_prompt,
                ),
                ("human", "previous message being replied to: {replied_to_message_content}. New message: {input}"),
            ]
        )

        self.__setupLLMs()
        
        self.llm_chain = self.prompt | self.current_llm

    async def call(self, input: str, replied_to_message_content: str = ""):
        prompt_args = {"input": input, "replied_to_message_content": replied_to_message_content}

        try:
            response = await self.llm_chain.ainvoke(prompt_args)
            logger.debug(f"AI response: {response}")
            return response.content
        except ConnectError as e:
            logger.error(f"Error caught. Using fallback LLM.")
            try:
                self.__llm_cycle()
                self.llm_chain = self.prompt | self.current_llm
                response = await self.llm_chain.ainvoke(prompt_args)
                logger.debug(f"AI response after fallback: {response}")
                return response.content
            except Exception as e:
                logger.error(f"Unexpected error caught. Error message: {str(e)}")
                return "AI Error"
            
    def __setupLLMs(self):
        if self.ollama_endpoint:
            self.ollama_llm = self.__setupOllamaLLM(self.ollama_endpoint)
            self.ollama_llm.bind_tools(self.tools)
        
        if self.groq_llm_model:
            self.groq_llm = self.__setupGroqLLM(self.groq_llm_model)
            self.groq_llm.bind_tools(self.tools)

        if self.google_llm_model:
            self.google_llm = self.__setupGoogleLLM(self.google_llm_model)
            self.google_llm.bind_tools(self.tools)

        self.current_llm = self.ollama_llm
        self.fallback_llms = [self.google_llm, self.groq_llm]

    
    def __setupGroqLLM(self, groq_llm_model: str):
        return ChatGroq(
            model=groq_llm_model,
            temperature=0.0,
            max_retries=2,
        )

    def __setupOllamaLLM(self, ollama_endpoint: str):
        return ChatOllama(
            base_url=ollama_endpoint,
            model="llama3.2",
            num_predict=330,
            temperature=0,
        )
    
    def __setupGoogleLLM(self, google_llm_model: str):
        return ChatGoogleGenerativeAI(
            model=google_llm_model,
            temperature=0.0,
            max_retries=2,
        )
    
    def __llm_cycle(self):
        # Cycle through fallback_llms list, rotating the first element to the end.
        self.current_llm = self.fallback_llms[0]
        self.fallback_llms = self.fallback_llms[1:] + [self.fallback_llms[0]]

    def __get_tools(self):
        @tool
        def web_search_text_ddg(query: str) -> List[Dict]:
            """Search the web for text content using DuckDuckGo."""
            results = DDGS.text(query, max_results=10)
            logger.info(results)
            return 
        
        @tool
        def web_search_image_ddg(query: str) -> List[Dict]:
            """Search the web for images using DuckDuckGo."""
            return DDGS.images(query, max_results=10)
        
        return [web_search_text_ddg, web_search_image_ddg]