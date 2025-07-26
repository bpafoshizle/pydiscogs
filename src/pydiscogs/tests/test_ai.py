"""test_ai.py
 testing ai cog

isort:skip_file
"""

import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv
from pydiscogs.cogs.ai import AI, AIHandler, AIReplyModal
from discord.ext import commands
from httpx import ConnectError
from langchain_core.messages import AIMessage

load_dotenv(override=True)
events = []


class TestAIHandler(unittest.IsolatedAsyncioTestCase):
    @patch("pydiscogs.cogs.ai.ChatGoogleGenerativeAI")
    def test_ai_handler_initialization_google(self, MockChatGoogleGenerativeAI):
        # Test AIHandler initialization with Google LLM
        ai_handler = AIHandler(
            google_api_key="test_google_api_key", google_llm_model="test_model"
        )
        self.assertIsInstance(ai_handler.current_llm, type(MockChatGoogleGenerativeAI.return_value))

    @patch("pydiscogs.cogs.ai.ChatOllama")
    def test_ai_handler_initialization_ollama(self, MockChatOllama):
        # Test AIHandler initialization with Ollama LLM
        ai_handler = AIHandler(
            ollama_endpoint="http://test_endpoint", ollama_llm_model="test_model"
        )
        self.assertIsInstance(ai_handler.current_llm, type(MockChatOllama.return_value))

    @patch("pydiscogs.cogs.ai.ChatGroq")
    def test_ai_handler_initialization_groq(self, MockChatGroq):
        # Test AIHandler initialization with Groq LLM
        ai_handler = AIHandler(groq_api_key="test_api_key", groq_llm_model="test_model")
        self.assertIsInstance(ai_handler.current_llm, type(MockChatGroq.return_value))

    def test_ai_handler_initialization_no_llm(self):
        # Test AIHandler initialization with no LLM specified
        with self.assertRaises(ValueError):
            AIHandler()

    @patch("pydiscogs.cogs.ai.create_react_agent")
    @patch("pydiscogs.cogs.ai.ChatGoogleGenerativeAI")
    async def test_ai_handler_call(self, MockChatGoogleGenerativeAI, mock_create_react_agent):
        # Test AIHandler.call method
        mock_llm = MockChatGoogleGenerativeAI.return_value
        async def mock_astream():
            yield {"messages": [AIMessage("test response")]}
        mock_create_react_agent.return_value.astream.return_value = mock_astream()

        ai_handler = AIHandler(
            google_api_key="test_google_api_key", google_llm_model="test_model"
        )
        ai_handler.current_agent = mock_create_react_agent.return_value
        response = await ai_handler.call("test input")
        self.assertEqual(response, "test response")

    @patch("pydiscogs.cogs.ai.create_react_agent")
    @patch("pydiscogs.cogs.ai.ChatGoogleGenerativeAI")
    async def test_ai_handler_call_fallback(
        self, MockChatGoogleGenerativeAI, mock_create_react_agent
    ):
        # Test AIHandler.call method with fallback
        mock_llm = MockChatGoogleGenerativeAI.return_value
        async def mock_astream():
            yield {"messages": [AIMessage("test response")]}
        mock_create_react_agent.return_value.astream.side_effect = [
            ConnectError("initial call failed"),
            mock_astream(),
        ]

        ai_handler = AIHandler(
            google_api_key="test_google_api_key", google_llm_model="test_model"
        )
        ai_handler.current_agent = mock_create_react_agent.return_value
        ai_handler.fallback_llms = [mock_llm]  # Set up a fallback LLM
        response = await ai_handler.call("test input")
        self.assertEqual(response, "test response")

    @patch("pydiscogs.cogs.ai.create_react_agent")
    @patch("pydiscogs.cogs.ai.ChatGoogleGenerativeAI")
    async def test_ai_handler_call_unexpected_error(
        self, MockChatGoogleGenerativeAI, mock_create_react_agent
    ):
        # Test AIHandler.call method with unexpected error
        mock_llm = MockChatGoogleGenerativeAI.return_value
        mock_create_react_agent.return_value.astream.side_effect = Exception(
            "initial call failed"
        )

        ai_handler = AIHandler(
            google_api_key="test_google_api_key", google_llm_model="test_model"
        )
        ai_handler.current_agent = mock_create_react_agent.return_value
        ai_handler.fallback_llms = []  # No fallback LLMs to trigger unexpected error
        response = await ai_handler.call("test input")
        self.assertEqual(response, "AI Error")

    # @patch("pydiscogs.cogs.ai.Client")
    # def test_web_research_tool(self, MockClient):
    #     # Test web_research tool
    #     ai_handler = AIHandler(
    #         google_api_key="test_google_api_key", google_llm_model="test_model"
    #     )
    #     mock_response = MagicMock()
    #     mock_response.candidates = [MagicMock()]
    #     mock_response.candidates[0].grounding_metadata.grounding_chunks = []
    #     mock_response.text = "test response"
    #     MockClient.return_value.models.generate_content.return_value = mock_response

    #     tools = ai_handler._AIHandler__get_tools()
    #     web_research = tools[0]
    #     result = web_research.func("test query")

    #     self.assertEqual(result, "test response")

# class TestAI(unittest.IsolatedAsyncioTestCase):
#     def setUp(self):
#         self.bot = commands.Bot(command_prefix=".")
#         events.append("setUp")

#     async def asyncSetUp(self):
#         self.ai_cog = AI(
#             bot=self.bot,
#             ollama_endpoint=os.getenv("OLLAMA_ENDPOINT"),
#             ollama_llm_model=os.getenv("OLLAMA_LLM_MODEL"),
#             google_api_key=os.getenv("GOOGLE_API_KEY"),
#             google_llm_model=os.getenv("GOOGLE_LLM_MODEL"),
#             groq_api_key=os.getenv("GROQ_API_KEY"),
#             groq_llm_model=os.getenv("GROQ_LLM_MODEL"),
#             ai_system_prompt=os.getenv("AI_SYSTEM_PROMPT"),
#         )
#         events.append("asyncSetUp")

#     def tearDown(self):
#         events.append("tearDown")

#     async def asyncTearDown(self):
#         await asyncio.sleep(0.5)  # https://github.com/aio-libs/aiohttp/issues/1115
#         events.append("asyncTearDown")

#     async def on_cleanup(self):
#         events.append("cleanup")

#     async def test_ai_call_returns_proper_response(self):
#         """
#         Test that calling the AI returns a proper response
#         """
#         events.append("test_ai_call_returns_proper_response")
#         response = await self.ai_cog.ai_handler.call(
#             input="What if I value foundations of logic or set theory??",
#             replied_to_message_content="""That's a tough one, man. There's no single GOAT in math, it's too subjective! But some names that always come up are Euler, Gauss, Newton, and Archimedes. Depends on what criteria you value most!""",
#         )
#         self.assertTrue(isinstance(response, str))
#         self.assertGreaterEqual(len(response), 1)
#         self.addAsyncCleanup(self.on_cleanup)

#     @patch("pydiscogs.cogs.ai.AIHandler")
#     async def test_ask_ai(self, MockAIHandler):
#         # Test ask_ai command
#         mock_context = MagicMock()
#         mock_context.respond = MagicMock()
#         mock_ai_handler = MockAIHandler.return_value
#         mock_ai_handler.call.return_value = "test response"

#         ai_cog = AI(bot=MagicMock())
#         ai_cog.ai_handler = mock_ai_handler
#         await ai_cog.ask_ai(mock_context, "test input")

#         mock_context.defer.assert_called()
#         mock_context.respond.assert_called_with("test response")

#     @patch("pydiscogs.cogs.ai.AIReplyModal")
#     async def test_ai_reply(self, MockAIReplyModal):
#         # Test ai_reply command
#         mock_context = MagicMock()
#         mock_context.send_modal = MagicMock()
#         mock_message = MagicMock()
#         mock_message.content = "test message"

#         ai_cog = AI(bot=MagicMock())
#         await ai_cog.ai_reply(mock_context, mock_message)

#         mock_context.send_modal.assert_called()

#     @patch("pydiscogs.cogs.ai.AIHandler")
#     async def test_ai_command(self, MockAIHandler):
#         # Test ai command
#         mock_context = MagicMock()
#         mock_context.send = MagicMock()
#         mock_message = MagicMock()
#         mock_context.message = mock_message
#         mock_message.reference = None
#         mock_ai_handler = MockAIHandler.return_value
#         mock_ai_handler.call.return_value = "test response"

#         ai_cog = AI(bot=MagicMock())
#         ai_cog.ai_handler = mock_ai_handler
#         await ai_cog.ai(mock_context, input="test input")

#         mock_context.send.assert_called_with("test response")

#     @patch("pydiscogs.cogs.ai.AIHandler")
#     async def test_on_message(self, MockAIHandler):
#         # Test on_message event
#         mock_message = MagicMock()
#         mock_message.author.id = 123
#         mock_bot = MagicMock()
#         mock_bot.user.id = 456
#         mock_message.mentions = [mock_bot.user]
#         mock_message.content = "test message"
#         mock_message.reply = MagicMock()
#         mock_ai_handler = MockAIHandler.return_value
#         mock_ai_handler.call.return_value = "test response"

#         ai_cog = AI(bot=mock_bot)
#         ai_cog.ai_handler = mock_ai_handler
#         await ai_cog.on_message(mock_message)

#         mock_message.reply.assert_called_with("test response")


# class TestAIReplyModal(unittest.IsolatedAsyncioTestCase):
#     @patch("discord.ui.Modal.__init__")
#     async def test_callback(self, mock_modal_init):
#         # Test callback method of AIReplyModal
#         mock_modal_init.return_value = None
#         mock_interaction = MagicMock()
#         mock_interaction.response.defer = MagicMock()
#         mock_interaction.followup.send = MagicMock()
#         mock_ai_handler = MagicMock()
#         mock_ai_handler.call.return_value = "test response"

#         modal = AIReplyModal(
#             ai_handler=mock_ai_handler, message_content="test message"
#         )
#         modal.children = [MagicMock()]
#         modal.children[0].value = "test prompt"

#         await modal.callback(mock_interaction)

#         mock_interaction.response.defer.assert_called()
#         mock_interaction.followup.send.assert_called_with("test response")

if __name__ == "__main__":
    unittest.main()
