""" test_wotd.py
    testing word of the day

   isort:skip_file
"""
import asyncio
import os
import unittest

# from icecream import ic
from unittest import IsolatedAsyncioTestCase  # pylint: disable=no-name-in-module

from discord.ext import commands
from pydiscogs.cogs.stocks import StockQuote

events = []

stock_list = [
    "TSLA",
    "TSN",
    "GME",
    "QQQ",
    "BTC-USD",
    "ETC-USD",
]


class TestStockQuote(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = commands.Bot(command_prefix=".")
        self.stock_cog = StockQuote(
            self.bot,
            stock_list,
            discord_post_channel_id="NA",
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

    async def test_getLatestStockQuote_returns_proper_response(self):
        """
        Test that the function returns a proper response
        """
        events.append("test_getLatestStockQuote_returns_proper_response")
        (
            symbol,
            name,
            lastprice,
            change,
            pctchange,
            quotetime,
            earnings_date,
        ) = await self.stock_cog.getLatestStockQuote("VTSAX")
        # ic(symbol, name, lastprice, change, quotetime)
        self.assertTrue(isinstance(symbol, str))
        self.assertGreater(len(symbol), 0)
        self.assertTrue(isinstance(name, str))
        self.assertGreater(len(name), 0)
        self.assertTrue(isinstance(lastprice, str))
        self.assertGreater(len(lastprice), 0)
        self.assertTrue(lastprice.isnumeric)
        self.assertTrue(isinstance(change, str))
        self.assertGreater(len(change), 0)
        self.assertTrue(isinstance(pctchange, str))
        self.assertGreater(len(pctchange), 0)
        self.assertTrue(isinstance(quotetime, str))
        self.assertGreater(len(quotetime), 0)
        self.assertTrue(isinstance(earnings_date, str))
        self.assertGreater(len(quotetime), 0)
        self.addAsyncCleanup(self.on_cleanup)

    async def test_getPrevClose_returns_proper_response(self):
        """
        Test that the function returns a proper response
        """
        events.append("test_getPrevClose_returns_proper_response")
        (symbol, prev_close, prev_high, prev_low) = await self.stock_cog.getPrevClose(
            "SPY"
        )
        # ic((symbol, prev_close, prev_high, prev_low))
        self.assertTrue(isinstance(symbol, str))
        self.assertGreater(len(symbol), 0)
        self.assertTrue(isinstance(prev_close, float))
        self.assertTrue(isinstance(prev_high, float))
        self.assertTrue(isinstance(prev_low, float))
        self.addAsyncCleanup(self.on_cleanup)

    async def test_getLatestMarketWatch_returns_proper_response(self):
        """
        Test that the function returns a proper response
        """
        events.append("test_getLatestMarketWatch_returns_proper_response")
        news = await self.stock_cog.getLatestNewsStockList()
        # ic(news)
        self.assertTrue(isinstance(news, list))
        self.assertGreaterEqual(len(news), 5)


if __name__ == "__main__":
    unittest.main()
