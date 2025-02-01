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
        self.ai_handler = AIHandler(
            ollama_endpoint, groq_api_key, groq_llm_model, ai_system_prompt
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
                ("human", "replied to message: {replied_to_message_content}"),
                ("human", "{input}"),
            ]
        )

        self.ollama_llm = self.__setupOllamaLLM(ollama_endpoint)
        self.groq_llm = self.__setupGroqLLM(groq_llm_model)
        
        if ollama_endpoint and groq_api_key:
            self.current_llm = self.ollama_llm
            self.fallback_llm = self.groq_llm

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
                self.__llm_swap()
                self.llm_chain = self.prompt | self.current_llm
                response = await self.llm_chain.ainvoke(prompt_args)
                logger.debug(f"AI response after fallback: {response}")
                return response.content
            except Exception as e:
                logger.error(f"Unexpected error caught. Error message: {str(e)}")
                return "AI Error"
    
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