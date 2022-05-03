""" test_twitch.py
    testing twitch of the day

   isort:skip_file
"""
import asyncio
import datetime
import os
import unittest

import twitchio

# from icecream import ic
from unittest import IsolatedAsyncioTestCase  # pylint: disable=no-name-in-module

from discord.ext import commands
from pydiscogs.cogs.twitch import Twitch

events = []

join_channels_list = ["bpafoshizle", "ephenry84", "elzblazin", "kuhouseii", "fwm_bot"]

follow_channels_list = [
    "JackFrags",
    "TrueGameDataLive",
    "Stodeh",
]


class TestTwitch(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = commands.Bot(command_prefix=".")
        self.twitch_cog = Twitch(
            self.bot,
            None,
            os.getenv("TWITCH_BOT_CLIENT_ID"),
            os.getenv("TWITCH_BOT_CLIENT_SECRET"),
            os.getenv("DSCRD_CHNL_GAMING"),
            join_channels_list,
            follow_channels_list,
        )
        events.append("setUp")

    async def asyncSetUp(self):
        events.append("asyncSetUp")

    def tearDown(self):
        events.append("tearDown")

    async def asyncTearDown(self):
        await self.twitch_cog.twitch_client._http.session.close()
        # await self.twitch_cog.bot._websocket.close()
        await asyncio.sleep(0.5)  # https://github.com/aio-libs/aiohttp/issues/1115
        events.append("asyncTearDown")

    async def on_cleanup(self):
        events.append("cleanup")

    async def test_get_stream_data_returns_proper_response(self):
        """
        Test that the function returns a proper response
        """
        events.append("test_get_stream_data_returns_proper_response")
        random_live_channel = (await self.twitch_cog.get_live_channels())[0]
        # ic(random_live_channel)
        streams = await self.twitch_cog.get_stream_data([random_live_channel.name])
        # ic(streams)
        self.assertGreaterEqual(len(streams), 1)
        stream = streams[0]
        self.assertTrue(isinstance(stream.user, twitchio.user.PartialUser))
        self.assertTrue(isinstance(stream.user.name, str))

        full_user = await stream.user.fetch()
        self.assertTrue(isinstance(full_user, twitchio.user.User))
        self.assertTrue(isinstance(full_user.display_name, str))
        self.assertTrue(isinstance(full_user.profile_image, str))
        self.assertTrue(isinstance(stream.title, str))
        self.assertTrue(isinstance(stream.game_name, str))
        self.assertTrue(isinstance(stream.started_at, datetime.datetime))
        self.addAsyncCleanup(self.on_cleanup)


if __name__ == "__main__":
    unittest.main()
