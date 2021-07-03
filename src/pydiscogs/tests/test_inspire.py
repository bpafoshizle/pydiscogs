import unittest
from unittest import (
    IsolatedAsyncioTestCase,
)  # pylint: disable=no-name-in-module

from discord.ext import commands
from pydiscogs.inspire import InspireQuote

events = []


class TestInspireQuote(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = commands.Bot(command_prefix=".")
        self.inspire_cog = InspireQuote(self.bot)
        events.append("setUp")

    async def asyncSetUp(self):
        events.append("asyncSetUp")

    def tearDown(self):
        events.append("tearDown")

    async def asyncTearDown(self):
        events.append("asyncTearDown")

    async def on_cleanup(self):
        events.append("cleanup")

    async def test_get_quote_returns_string(self):
        """
        Test that the function returns a valid non-empty string
        """
        events.append("test_get_quote_returns_string")
        quote = await self.inspire_cog.get_quote()
        self.assertTrue(isinstance(quote, str))
        self.assertGreater(len(quote), 0)
        self.addAsyncCleanup(self.on_cleanup)


if __name__ == "__main__":
    unittest.main()
