import logging
import os

from discord.ext import commands
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)

class AI(commands.Cog):
    def __init__(
        self,
        bot,
        ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT"),
        groq_api_key: str = os.getenv("GROQ_API_KEY"),
        ai_system_prompt: str = os.getenv("AI_SYSTEM_PROMPT")
    ):
        if ollama_endpoint is None and groq_api_key is None:
            raise ValueError(
                "Must specify either ollama_endpoint or groq_api_key"
            )
        
        if ollama_endpoint:
            self.ollama_llm = ChatOllama(
                base_url=ollama_endpoint,
                model="llama3.2",
                system=ai_system_prompt,
                temperature=0,
            )

        
        # TODO: if both Ollama and groq are specified, try ollama first, fall back to 
        # groq.
        
        self.bot = bot


    @commands.slash_command()
    async def ai(self, ctx, prompt: str):
        try:
            response = self.ollama_llm.invoke(prompt)
            await ctx.respond(response)
        except Exception as e:
            print(f"Error in AI command: {e}")