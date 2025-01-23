import logging
import os
from httpx import ConnectError

import discord
from discord.ext import commands
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class AI(commands.Cog):
    def __init__(
        self,
        bot,
        ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT"),
        groq_api_key: str = os.getenv("GROQ_API_KEY"),
        groq_llm_model: str = os.getenv("GROQ_LLM_MODEL"),
        ai_system_prompt: str = os.getenv("AI_SYSTEM_PROMPT")
    ):
        if ollama_endpoint is None and groq_api_key is None:
            raise ValueError(
                "Must specify either ollama_endpoint or groq_api_key"
            )
        
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    ai_system_prompt,
                ),
                ("human", "{input}"),
            ]
        )

        self.ollama_llm = self.__setupOllamaLLM(ollama_endpoint)
        self.groq_llm = self.__setupGroqLLM(groq_llm_model)
        
        if ollama_endpoint and groq_api_key:
            self.current_llm = self.ollama_llm
            self.fallback_llm = self.groq_llm
        # else:
        #     self.ollama_llm = ChatOllama(
        #         model="llama3.2",
        #         num_predict=330,
        #         temperature=0,
        #     )
        #     self.llm_chain = self.prompt | self.ollama_llm

        self.llm_chain = self.prompt | self.current_llm
        self.bot = bot

    @commands.slash_command()
    async def ai(self, ctx: discord.ApplicationContext, prompt: str):
        try:
            response = self.llm_chain.invoke(prompt)
            logger.debug(f"AI response: {response}")
            await ctx.respond(response.content)
        except ConnectError as e:
            logger.error(f"Error caught. Using fallback LLM.")
            try:
                self.__llm_swap()
                self.llm_chain = self.prompt | self.current_llm
                response = self.llm_chain.invoke(prompt)
                logger.debug(f"AI response after fallback: {response}")
                await ctx.respond(response.content)
            except Exception as e:
                logger.error(f"Unexpected error caught. Error message: {str(e)}")

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
    
    def __llm_swap(self):
        self.current_llm, self.fallback_llm = self.fallback_llm, self.current_llm