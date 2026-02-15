import base64
import contextlib
import io
import logging
import os
import textwrap

import discord
from discord.ext import commands
from httpx import ConnectError
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langgraph.store.base import IndexConfig

from .agent import build_agent_graph

# from .tools.computer_control import ComputerControlTool
from .tools.url_context import UrlContextTool
from .tools.web_research import WebResearchTool
from .tools.xai_research import XResearchTool

logger = logging.getLogger(__name__)


class GoogleGenerativeAIEmbeddingsWithDims(GoogleGenerativeAIEmbeddings):
    def embed_documents(self, texts, **kwargs):
        # Force dims to 768 to avoid HNSW limit (2000)
        return super().embed_documents(texts, output_dimensionality=768)

    def embed_query(self, text, **kwargs):
        # Force dims to 768 to avoid HNSW limit (2000)
        return super().embed_query(text, output_dimensionality=768)

    async def aembed_documents(self, texts, **kwargs):
        # Force dims to 768 to avoid HNSW limit (2000)
        return await super().aembed_documents(texts, output_dimensionality=768)

    async def aembed_query(self, text, **kwargs):
        # Force dims to 768 to avoid HNSW limit (2000)
        return await super().aembed_query(text, output_dimensionality=768)


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
        xai_api_key: str = os.getenv("XAI_API_KEY"),
        ai_system_prompt: str = os.getenv("AI_SYSTEM_PROMPT"),
        postgres_url: str = os.getenv("POSTGRES_DB_URL"),
    ):
        self.ai_handler = AIHandler(
            ollama_endpoint,
            ollama_llm_model,
            google_api_key,
            google_llm_model,
            groq_api_key,
            groq_llm_model,
            xai_api_key,
            ai_system_prompt,
            postgres_url,
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
    async def ask_ai(
        self,
        ctx: discord.ApplicationContext,
        input: str,
        attachment: discord.Attachment = None,
    ):
        await ctx.defer()
        images = []
        if (
            attachment
            and attachment.content_type
            and attachment.content_type.startswith("image/")
        ):
            images.append((await attachment.read(), attachment.content_type))
        response = await self.ai_handler.call(
            input,
            images=images,
            thread_id=str(ctx.interaction.id),
            user_id=str(ctx.author.id),
            guild_id=str(ctx.guild_id) if ctx.guild_id else None,
            channel_id=str(ctx.channel_id) if ctx.channel_id else None,
        )

        await self.send_response(ctx.followup, response)

    @commands.message_command(name="AI Reply")
    async def ai_reply(self, ctx, message: discord.Message):
        images = await self._get_images_from_message(message)
        modal = AIReplyModal(
            title="AI Reply",
            ai_handler=self.ai_handler,
            original_message=message,
            images=images,
            send_response_fn=self.send_response,
            get_root_message_fn=self._get_root_message,
        )
        await ctx.send_modal(modal)

    @commands.command()
    async def ai(self, ctx, *, input: str):
        images = await self._get_images_from_message(ctx.message)
        thread_id = await self._get_root_message(ctx.message)
        response = await self.ai_handler.call(
            input,
            images=images,
            thread_id=thread_id,
            user_id=str(ctx.author.id),
            guild_id=str(ctx.guild.id) if ctx.guild else None,
            channel_id=str(ctx.channel.id) if ctx.channel else None,
        )
        await self.send_response(ctx, response)

    async def _get_root_message(self, message: discord.Message) -> str:
        if not message.reference:
            return str(message.id)

        # Traverse up the chain
        current_msg = message
        while current_msg.reference:
            try:
                if current_msg.reference.cached_message:
                    current_msg = current_msg.reference.cached_message
                else:
                    channel = self.bot.get_channel(current_msg.reference.channel_id)
                    if channel:
                        current_msg = await channel.fetch_message(
                            current_msg.reference.message_id
                        )
                    else:
                        # Fallback if channel not found, return current message id as best effort root?
                        # Or maybe the reference ID itself if we can't fetch it?
                        # Reference object has message_id.
                        return str(current_msg.reference.message_id)
            except (discord.NotFound, discord.HTTPException):
                # If we can't find the parent, break and use current or reference ID.
                # Using the reference message_id is safer as "the oldest known ancestor"
                return str(current_msg.reference.message_id)

        return str(current_msg.id)

    async def _get_images_from_message(
        self, message: discord.Message
    ) -> list[tuple[bytes, str]]:
        images = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                images.append((await attachment.read(), attachment.content_type))
        return images

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages sent by the bot itself
        if message.author.id == self.bot.user.id:
            return

        # Check if the bot was mentioned in the message
        if self.bot.user in message.mentions:
            images = await self._get_images_from_message(message)
            # If the referenced message has images, we might want to include them?
            # The new memory system will handle text history.
            # For images in history, LangGraph *can* keep them in state if configured,
            # but for now let's assume we just want current message images + maybe simple current-reply context if we were keeping "replied_to" logic.
            # User instruction: "Remove the manual 'replied_to_message' injection"
            # So we rely on memory for text context. Images from previous turns should theoretically be in memory if we persist them.
            # But currently `get_images_from_message` was also looking at the replied-to message.
            # I'll keep the image extension logic just in case the user wants "images from the guy I'm replying to" to be visible immediately as input for THIS turn.

            if message.reference:
                try:
                    replied_to_message = await message.channel.fetch_message(
                        message.reference.message_id
                    )
                    images.extend(
                        await self._get_images_from_message(replied_to_message)
                    )
                except Exception:
                    pass

            thread_id = await self._get_root_message(message)

            response = await self.ai_handler.call(
                message.content,
                images=images,
                thread_id=thread_id,
                user_id=str(message.author.id),
                guild_id=str(message.guild.id) if message.guild else None,
                channel_id=str(message.channel.id) if message.channel else None,
            )
            await self.send_response(message, response)

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready. Initializes the AI handler."""
        logger.info("AI cog: bot is ready, initializing AI handler...")
        await self.ai_handler.initialize()

    # Allow other listeners and commands to process the message
    # await self.bot.process_commands(message)


class AIReplyModal(discord.ui.Modal):
    def __init__(
        self,
        *args,
        ai_handler,
        original_message: discord.Message,
        images=None,
        send_response_fn,
        get_root_message_fn,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.ai_handler = ai_handler
        self.original_message = original_message
        self.images = images
        self.send_response = send_response_fn
        self.get_root_message = get_root_message_fn
        self.add_item(
            discord.ui.InputText(label="Prompt", style=discord.InputTextStyle.long)
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        thread_id = await self.get_root_message(self.original_message)

        response = await self.ai_handler.call(
            self.children[0].value,
            images=self.images,
            thread_id=thread_id,
            user_id=str(interaction.user.id),
            guild_id=str(interaction.guild_id) if interaction.guild_id else None,
            channel_id=str(interaction.channel_id) if interaction.channel_id else None,
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
        xai_api_key: str = None,
        ai_system_prompt: str = None,
        postgres_url: str = None,
    ):
        self.ollama_endpoint = ollama_endpoint or os.getenv("OLLAMA_ENDPOINT")
        self.ollama_llm_model = ollama_llm_model or os.getenv("OLLAMA_LLM_MODEL")
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.google_llm_model = google_llm_model or os.getenv("GOOGLE_LLM_MODEL")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.groq_llm_model = groq_llm_model or os.getenv("GROQ_LLM_MODEL")
        self.xai_api_key = xai_api_key or os.getenv("XAI_API_KEY")
        self.ai_system_prompt = ai_system_prompt or os.getenv("AI_SYSTEM_PROMPT")
        self.postgres_url = postgres_url or os.getenv("POSTGRES_DB_URL")
        if self.postgres_url:
            self.postgres_url = self.postgres_url.strip("\"'")

        logger.info(
            f"AIHandler initialized with Postgres URL: {'[REDACTED]' if self.postgres_url else 'None'}"
        )

        self.checkpointer = None
        self.store = None
        self.pool = None

        if not any([self.ollama_endpoint, self.groq_api_key, self.google_api_key]):
            raise ValueError(
                "Must specify either ollama_endpoint, groq_api_key, or google_api_key"
            )

        self.tools = self.__get_tools()

        self.__setupLLMs()

    async def initialize(self):
        """Initializes the Postgres connection, checkpointer, and store."""
        if not self.postgres_url:
            logger.warning("AIHandler: No POSTGRES_DB_URL found. Persistence disabled.")
            return

        if self.checkpointer:
            logger.debug("AIHandler: Already initialized.")
            return

        logger.info("AIHandler: Initializing Postgres connection and tables...")
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from langgraph.store.postgres.aio import AsyncPostgresStore
            from psycopg_pool import AsyncConnectionPool

            connection_kwargs = {
                "autocommit": True,
                "prepare_threshold": 0,
            }
            self.pool = AsyncConnectionPool(
                conninfo=self.postgres_url,
                max_size=10,
                kwargs=connection_kwargs,
                open=False,
            )
            await self.pool.open()
            self.checkpointer = AsyncPostgresSaver(self.pool)
            await self.checkpointer.setup()

            # Initialize embeddings for semantic search
            embeddings = GoogleGenerativeAIEmbeddingsWithDims(
                model="models/gemini-embedding-001",
                google_api_key=self.google_api_key,
            )

            # Configure store with vector index
            index_config = IndexConfig(dims=768, embed=embeddings, fields=["data"])

            self.store = AsyncPostgresStore(self.pool, index=index_config)
            await self.store.setup()
            logger.info(
                "AIHandler: AsyncPostgresStore with Vector Index initialized successfully."
            )

            # Re-initialize agent with checkpointer and store
            self.__setupLLMs()
        except Exception as e:
            logger.error(
                f"AIHandler: Failed to initialize Postgres: {e}", exc_info=True
            )
            self.checkpointer = None
            self.store = None
            if self.pool:
                await self.pool.close()
                self.pool = None

    async def call(
        self,
        input: str,
        images: list[tuple[bytes, str]] = None,
        thread_id: str = "default",
        user_id: str = "default_user",
        guild_id: str = None,
        channel_id: str = None,
    ):
        logger.debug(
            f"AIHandler.call invoked. Store is not None: {self.store is not None}"
        )
        if self.postgres_url and not self.checkpointer:
            await self.initialize()

        content = []
        content.append({"type": "text", "text": input})

        if images:
            for image_bytes, content_type in images:
                encoded = base64.b64encode(image_bytes).decode("utf-8")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": f"data:{content_type};base64,{encoded}",
                    }
                )

        messages = {"messages": [HumanMessage(content=content)]}
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
                "guild_id": guild_id,
                "channel_id": channel_id,
            }
        }

        try:
            async for step in self.current_agent.astream(
                messages,
                config=config,
                stream_mode="values",
            ):
                response = step["messages"][-1]
                logger.debug(
                    "\n"
                    + self.__get_pretty_print_response_string(
                        self.__sanitize_message(response)
                    )
                )
            logger.info(f"response: {self.__sanitize_message(response)}")
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
                    config=config,
                    stream_mode="values",
                ):
                    response = step["messages"][-1]
                    logger.debug(
                        "\n"
                        + self.__get_pretty_print_response_string(
                            self.__sanitize_message(response)
                        )
                    )
                final_content = response.content
                if isinstance(final_content, list):
                    return final_content[0].get(
                        "text", "Sorry, I couldn't parse the response."
                    )
                return final_content
            except Exception as e:
                logger.debug("Exception caught in fallback", exc_info=True)
                logger.error(f"Unexpected error caught. Error message: {str(e)}")
                return "AI Error"
        except Exception as e:
            logger.debug("Exception caught in fallback", exc_info=True)
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

        self.current_agent = build_agent_graph(
            self.current_llm,
            self.tools,
            system_prompt=self.ai_system_prompt,
            checkpointer=self.checkpointer,
            store=self.store,
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
        self.current_agent = build_agent_graph(
            self.current_llm,
            self.tools,
            system_prompt=self.ai_system_prompt,
            checkpointer=self.checkpointer,
            store=self.store,
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

        if self.xai_api_key:
            tools.append(XResearchTool(xai_api_key=self.xai_api_key))

        return tools

    def __get_pretty_print_response_string(self, response):
        pretty_output = ""
        # Capture pretty_print output:
        with io.StringIO() as buf, contextlib.redirect_stdout(buf):
            response.pretty_print()
            pretty_output = buf.getvalue()

        return pretty_output

    def __sanitize_message(self, message):
        """Sanitize message for logging by truncating large base64 image data."""
        import copy

        if not isinstance(message.content, list):
            return message

        sanitized_content = []
        for item in message.content:
            if isinstance(item, dict) and item.get("type") == "image_url":
                # Create a copy and truncate the base64 data
                new_item = copy.deepcopy(item)
                image_url = new_item.get("image_url", "")
                if ";base64," in image_url:
                    parts = image_url.split(";base64,")
                    new_item["image_url"] = parts[0] + ";base64,...[TRUNCATED]"
                sanitized_content.append(new_item)
            else:
                sanitized_content.append(item)

        sanitized_message = copy.copy(message)
        sanitized_message.content = sanitized_content
        return sanitized_message
