import contextlib
import io
import logging
import os
import textwrap

import discord
from discord.ext import commands
from httpx import ConnectError
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from .tools.url_context import UrlContextTool
from .tools.web_research import WebResearchTool

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

    @staticmethod
    async def send_response(destination, response: str):
        wrapper = textwrap.TextWrapper(
            width=2000,
            break_long_words=True,
            replace_whitespace=False,
            break_on_hyphens=False,
        )
        chunks = wrapper.wrap(response)

        if not chunks:
            return

        # First chunk
        first_chunk = chunks.pop(0)

        # Determine how to send the first message
        if isinstance(destination, discord.Message):
            # Reply to a message
            await destination.reply(first_chunk)
            # Subsequent messages go to the same channel
            for chunk in chunks:
                await destination.channel.send(chunk)
        elif isinstance(destination, commands.Context):
            # Send to command context channel
            await destination.send(first_chunk)
            for chunk in chunks:
                await destination.send(chunk)
        elif isinstance(destination, discord.Webhook):
            # Send to a webhook (from a deferred interaction)
            await destination.send(first_chunk)
            for chunk in chunks:
                await destination.send(chunk)
        else:
            raise TypeError(f"Unsupported destination type: {type(destination)}")

    @commands.slash_command()
    async def ask_ai(self, ctx: discord.ApplicationContext, input: str):
        await ctx.defer()
        response = await self.ai_handler.call(input)
        await self.send_response(ctx.followup, response)

    @commands.message_command(name="AI Reply")
    async def ai_reply(self, ctx, message: discord.Message):
        modal = AIReplyModal(
            title="AI Reply",
            ai_handler=self.ai_handler,
            message_content=message.content,
            send_response_fn=self.send_response,
        )
        await ctx.send_modal(modal)

    @commands.command()
    async def ai(self, ctx, *, input: str):
        replied_to_message_content = None
        if ctx.message.reference:
            replied_to_message_content = (
                await ctx.fetch_message(ctx.message.reference.message_id)
            ).content
        response = await self.ai_handler.call(input, replied_to_message_content)
        await self.send_response(ctx, response)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages sent by the bot itself
        if message.author.id == self.bot.user.id:
            return

        # Check if the bot was mentioned in the message
        if self.bot.user in message.mentions:
            # await message.reply("Thanks for mentioning me!")  # Reply to the message
            replied_to_message_content = None
            if message.reference:
                replied_to_message_content = (
                    await message.channel.fetch_message(message.reference.message_id)
                ).content
            response = await self.ai_handler.call(
                message.content, replied_to_message_content
            )
            await self.send_response(message, response)

        # Allow other listeners and commands to process the message
        # await self.bot.process_commands(message)


class AIReplyModal(discord.ui.Modal):
    def __init__(
        self, *args, ai_handler, message_content, send_response_fn, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.ai_handler = ai_handler
        self.message_content = message_content
        self.send_response = send_response_fn
        self.add_item(
            discord.ui.InputText(label="Prompt", style=discord.InputTextStyle.long)
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        response = await self.ai_handler.call(
            self.children[0].value, self.message_content
        )
        await self.send_response(interaction.followup, response)


class AIHandler:
    def __init__(
        self,
        ollama_endpoint: str = None,
        ollama_llm_model: str = None,
        google_api_key: str = None,
        google_llm_model: str = None,
        groq_api_key: str = None,
        groq_llm_model: str = None,
        ai_system_prompt: str = None,
    ):
        self.ollama_endpoint = ollama_endpoint or os.getenv("OLLAMA_ENDPOINT")
        self.ollama_llm_model = ollama_llm_model or os.getenv("OLLAMA_LLM_MODEL")
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.google_llm_model = google_llm_model or os.getenv("GOOGLE_LLM_MODEL")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.groq_llm_model = groq_llm_model or os.getenv("GROQ_LLM_MODEL")
        self.ai_system_prompt = ai_system_prompt or os.getenv("AI_SYSTEM_PROMPT")

        if not any([self.ollama_endpoint, self.groq_api_key, self.google_api_key]):
            raise ValueError(
                "Must specify either ollama_endpoint, groq_api_key, or google_api_key"
            )

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
            logger.info(f"response: {response}")
            final_content = response.content
            if isinstance(final_content, list):
                return final_content[0].get(
                    "text", "Sorry, I couldn't parse the response."
                )
            return final_content
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
                final_content = response.content
                if isinstance(final_content, list):
                    return final_content[0].get(
                        "text", "Sorry, I couldn't parse the response."
                    )
                return final_content
            except Exception as e:
                logger.error(f"Unexpected error caught. Error message: {str(e)}")
                return "AI Error"
        except Exception as e:
            logger.error(f"Unexpected error caught. Error message: {str(e)}")
            return "AI Error"

    def __setupLLMs(self):
        if self.ollama_endpoint:
            self.ollama_llm = self.__setupOllamaLLM(
                self.ollama_endpoint, self.ollama_llm_model
            )
        else:
            self.ollama_llm = None

        if self.groq_llm_model:
            self.groq_llm = self.__setupGroqLLM(self.groq_llm_model)
        else:
            self.groq_llm = None

        if self.google_llm_model:
            self.google_llm = self.__setupGoogleLLM(self.google_llm_model)
        else:
            self.google_llm = None

        llms = [self.google_llm, self.ollama_llm, self.groq_llm]
        self.current_llm = next((llm for llm in llms if llm), None)
        self.fallback_llms = [
            llm for llm in llms if llm != self.current_llm and llm is not None
        ]

        self.current_agent = create_agent(
            self.current_llm, self.tools, system_prompt=self.ai_system_prompt
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
        self.current_agent = create_agent(
            self.current_llm, self.tools, system_prompt=self.ai_system_prompt
        )

    def __get_tools(self):
        tools = []
        if self.google_api_key and self.google_llm_model:
            tools.extend(
                [
                    WebResearchTool(
                        google_api_key=self.google_api_key,
                        google_llm_model=self.google_llm_model,
                    ),
                    UrlContextTool(
                        google_api_key=self.google_api_key,
                        google_llm_model=self.google_llm_model,
                    ),
                ]
            )
        return tools

    def __get_pretty_print_response_string(self, response):
        pretty_output = ""
        # Capture pretty_print output:
        with io.StringIO() as buf, contextlib.redirect_stdout(buf):
            response.pretty_print()
            pretty_output = buf.getvalue()

        return pretty_output
