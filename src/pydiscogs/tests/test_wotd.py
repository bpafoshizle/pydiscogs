""" test_wotd.py
    testing word of the day

   isort:skip_file
"""

import asyncio
import os
import unittest

from unittest import IsolatedAsyncioTestCase  # pylint: disable=no-name-in-module

from discord.ext import commands
from pydiscogs.cogs.wotd import WordOfTheDay

events = []


class TestWordOfTheDay(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = commands.Bot(command_prefix=".")
        self.wotd_cog = WordOfTheDay(self.bot, os.getenv("DSCRD_CHNL_GENERAL"))
        events.append("setUp")

    async def asyncSetUp(self):
        events.append("asyncSetUp")

    def tearDown(self):
        events.append("tearDown")

    async def asyncTearDown(self):
        await asyncio.sleep(0.1)  # https://github.com/aio-libs/aiohttp/issues/1115
        events.append("asyncTearDown")

    async def on_cleanup(self):
        events.append("cleanup")

    async def test_get_word_of_the_day_returns_proper_response(self):
        """
        Test that the function returns a proper response
        """
        events.append("test_get_word_of_the_day_returns_proper_response")
        (
            word,
            word_syllables,
            part_of_speech,
            definitions,
        ) = await self.wotd_cog.get_word_of_the_day()
        self.assertTrue(isinstance(word, str))
        self.assertGreater(len(word), 0)
        self.assertTrue(isinstance(word_syllables, str))
        self.assertGreater(len(word_syllables), 0)
        self.assertTrue(isinstance(part_of_speech, str))
        self.assertGreater(len(part_of_speech), 0)
        self.assertTrue(isinstance(definitions, list))
        self.assertGreater(len(definitions), 0)
        self.addAsyncCleanup(self.on_cleanup)


if __name__ == "__main__":
    unittest.main()
