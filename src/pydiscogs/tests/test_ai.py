"""test_ai.py
 testing ai cog

isort:skip_file
"""

import asyncio
import os
import unittest

# from icecream import ic
from unittest import IsolatedAsyncioTestCase  # pylint: disable=no-name-in-module

from dotenv import load_dotenv
from discord.ext import commands
from pydiscogs.cogs.ai import AI

load_dotenv(override=True)
events = []


class TestAI(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = commands.Bot(command_prefix=".")
        events.append("setUp")

    async def asyncSetUp(self):
        self.ai_cog = AI(
            bot=self.bot,
            ollama_endpoint=os.getenv("OLLAMA_ENDPOINT"),
            ollama_llm_model=os.getenv("OLLAMA_LLM_MODEL"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            google_llm_model=os.getenv("GOOGLE_LLM_MODEL"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            groq_llm_model=os.getenv("GROQ_LLM_MODEL"),
            ai_system_prompt=os.getenv("AI_SYSTEM_PROMPT"),
        )
        events.append("asyncSetUp")

    def tearDown(self):
        events.append("tearDown")

    async def asyncTearDown(self):
        await asyncio.sleep(0.5)  # https://github.com/aio-libs/aiohttp/issues/1115
        events.append("asyncTearDown")

    async def on_cleanup(self):
        events.append("cleanup")

    async def test_ai_call_returns_proper_response(self):
        """
        Test that calling the AI returns a proper response
        """
        events.append("test_ai_call_returns_proper_response")
        response = await self.ai_cog.ai_handler.call(
            input="What if I value foundations of logic or set theory??",
            replied_to_message_content="""That's a tough one, man. There's no single GOAT in math, it's too subjective! But some names that always come up are Euler, Gauss, Newton, and Archimedes. Depends on what criteria you value most!""",
        )
        self.assertTrue(isinstance(response, str))
        self.assertGreaterEqual(len(response), 1)
        self.addAsyncCleanup(self.on_cleanup)


if __name__ == "__main__":
    unittest.main()
