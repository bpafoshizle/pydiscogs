""" test_reddit.py
    testing reddit cog

   isort:skip_file
"""
import asyncio
import os
import unittest

from typing import List

# from icecream import ic
from unittest import IsolatedAsyncioTestCase  # pylint: disable=no-name-in-module

from discord.embeds import Embed
from discord.ext import commands
from pydiscogs.reddit import Reddit

events = []


class TestReddit(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = commands.Bot(command_prefix=".")
        events.append("setUp")

    async def asyncSetUp(self):
        self.reddit_cog = Reddit(
            self.bot,
            os.getenv("REDDIT_CLIENT_ID"),
            os.getenv("REDDIT_CLIENT_SECRET"),
            os.getenv("REDDIT_USERNAME"),
            os.getenv("REDDIT_PASSWORD"),
            ["sexygirls", "battlefield"],
            os.getenv("GFYCAT_CLIENT_ID"),
            os.getenv("GFYCAT_CLIENT_SECRET"),
            os.getenv("DSCRD_DEV_CHNL_GENERAL"),
        )
        events.append("asyncSetUp")

    def tearDown(self):
        events.append("tearDown")

    async def asyncTearDown(self):
        await self.reddit_cog.reddit.requestor._http.close()
        await asyncio.sleep(0.5)  # https://github.com/aio-libs/aiohttp/issues/1115
        events.append("asyncTearDown")

    async def on_cleanup(self):
        events.append("cleanup")

    async def test_getTopEntry_returns_proper_response(self):
        """
        Test that the function returns a proper response
        """
        events.append("test_getTopEntry_returns_proper_response")
        posts = await self.reddit_cog.getTopEntry(self.reddit_cog.subreddit_list[0])
        # ic(posts)
        # ic(posts[0].title)
        self.assertTrue(isinstance(posts, List))
        self.assertGreaterEqual(len(posts), 1)
        self.assertTrue(isinstance(posts[0], Embed))
        self.assertTrue(isinstance(posts[0].title, str))
        self.assertTrue(isinstance(posts[0].url, str))
        self.assertTrue(isinstance(posts[0].image.url, str))
        self.addAsyncCleanup(self.on_cleanup)


if __name__ == "__main__":
    unittest.main()
