""" test_wotd.py
    testing word of the day

   isort:skip_file
"""
import asyncio
import datetime
import os
import unittest

from typing import List, Dict
# from icecream import ic
from unittest import IsolatedAsyncioTestCase  # pylint: disable=no-name-in-module

from discord.ext import commands
from pydiscogs.seekingalphanews import SeekingAlhpaNews

events = []

class TestStockQuote(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = commands.Bot(command_prefix=".")
        self.seekingalphanews_cog = SeekingAlhpaNews(
            self.bot,
            os.getenv("DSCRD_CHNL_MONEY"),
        )
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

    async def test_getMarketNews_returns_proper_response(self):
        """
        Test that the function returns a proper response
        """
        events.append("test_getMarketNews_returns_proper_response")
        news = await self.seekingalphanews_cog.getMarketNews()
        # ic(symbol, name, lastprice, change, quotetime)
        self.assertTrue(isinstance(news, List))
        self.assertGreater(len(news), 0)
        
        article = news[0]
        self.assertTrue(isinstance(article, Dict))
        self.assertTrue(isinstance(article["timestamp"], str or datetime.datetime))
        self.assertTrue(isinstance(article["source"], str))
        self.assertTrue(isinstance(article["title"], str))
        self.assertGreater(len(article["title"]), 0)
        self.assertTrue(isinstance(article["url"], str))
        self.assertGreater(len(article["url"]), 25)

if __name__ == "__main__":
    unittest.main()
