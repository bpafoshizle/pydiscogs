"""test_botbuilder.py
 testing bot builder

isort:skip_file
"""

import logging
import unittest
import warnings
from unittest import IsolatedAsyncioTestCase

from dotenv import load_dotenv
from pydiscogs import botbuilder
from pydiscogs.cogs.inspire import InspireQuote
from pydiscogs.cogs.wotd import WordOfTheDay
from pydiscogs.cogs.stocks import StockQuote
from pydiscogs.cogs.twitch import Twitch
from pydiscogs.cogs.reddit import Reddit

logging.disable(logging.CRITICAL)
load_dotenv(override=True)


class TestBotBuilder(IsolatedAsyncioTestCase):
    def setUp(self):
        warnings.simplefilter("ignore", category=DeprecationWarning)
        self.bot = botbuilder.build_bot("./src/pydiscogs/tests/testbot.yaml")

    def test_InspireQuote_cog_created(self):
        cog = self.bot.cogs.get("InspireQuote")
        self.assertTrue(isinstance(cog, InspireQuote))

    def test_WordOfTheDay_cog_created(self):
        cog = self.bot.cogs.get("WordOfTheDay")
        self.assertTrue(isinstance(cog, WordOfTheDay))

    def test_StockQuote_cog_created(self):
        cog = self.bot.cogs.get("StockQuote")
        self.assertTrue(isinstance(cog, StockQuote))

    def test_Twitch_cog_created(self):
        cog = self.bot.cogs.get("Twitch")
        self.assertTrue(isinstance(cog, Twitch))

    def test_Reddit_cog_created(self):
        cog = self.bot.cogs.get("Reddit")
        self.assertTrue(isinstance(cog, Reddit))


if __name__ == "__main__":
    unittest.main()
