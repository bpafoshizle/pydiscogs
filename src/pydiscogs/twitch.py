import logging
from datetime import datetime, timezone
from pprint import pprint
from typing import List
from uuid import UUID

import discord
import twitchio
from discord.ext import commands, tasks

from pydiscogs.utils.timing import fmt_datetime_to_minute, naive_to_us_central

logger = logging.getLogger(__name__)


class Twitch(commands.Cog):
    def __init__(
        self,
        bot,
        twitch_bot_client_id,
        twitch_bot_client_secret,
        discord_post_channel_id: int,
        join_channels_list,
        follow_channels_list,
    ):
        self.follow_channels_list = follow_channels_list
        self.join_channels_list = join_channels_list
        self.channel_states = self.init_channel_state(
            join_channels_list + follow_channels_list
        )
        self.discord_bot = bot
        self.user_data = None
        self.discord_post_channel_id = discord_post_channel_id
        self.twitch_client = twitchio.Client.from_client_credentials(
            client_id=twitch_bot_client_id, client_secret=twitch_bot_client_secret
        )

        # self.discord_bot.loop.create_task(self.bot.start())
        # pylint: disable=no-member
        self.check_channels_live_task.start()

        # Can't use event sub without internet accessible https callback endpoint
        # self.twitch_eventsub_client = eventsub.EventSubClient(
        #     client=self.twitch_client,
        #     webhook_secret=os.getenv("TWITCH_WEBHOOK_SECRET"),
        #     callback_route="https://bpafoshizle.com/webhooks/callback"
        # )

        # self.twitch_eventsub_client.subscribe_channel_stream_start(108647345)

    # Discord tasks and commandsnaive_to_us_central
    @tasks.loop(minutes=1)
    async def check_channels_live_task(self):
        logger.debug("channel id %s", self.discord_post_channel_id)
        chnl = self.discord_bot.get_channel(int(self.discord_post_channel_id))
        logger.debug("Got channel %s", chnl)
        streams = await self.get_stream_data(
            channels=self.join_channels_list + self.follow_channels_list
        )
        for stream in streams:
            logger.debug(stream)
            if self.channel_states[stream.user.name]["started_at"] < stream.started_at:
                self.channel_states[stream.user.name]["started_at"] = stream.started_at
                stream.user = await stream.user.fetch()
                logger.info(stream.user)
                await chnl.send(embed=self.formatStreamEmbed(stream))
            else:
                logger.info(
                    "User %s still streaming since %s",
                    stream.user.name,
                    self.channel_states[stream.user.name]["started_at"],
                )

    @check_channels_live_task.before_loop
    async def before(self):
        await self.discord_bot.wait_until_ready()
        logger.info("check_channels_live_task.before_loop: bot ready")

    @commands.command()
    async def twitch_getuser(self, ctx, user):
        response = await self.get_user_data([user])
        logger.debug(response)
        await ctx.send(embed=self.formatUserInfoEmbed(response[0]))

    # @commands.command()
    # async def twitch_getfollowers(self, ctx, username):
    #     userid, image_url = await self.info_from_name(username)
    #     response = await self.client.get_followers(int(userid))
    #     embed = self.formatFollowerInfoEmbed(
    #         username, image_url, self.parseFollowers(response)
    #     )
    #     logger.debug(response)
    #     await ctx.send(embed=embed)

    # TwitchIO command
    # async def sayhello(self, ctx):
    #     logger.debug("Discord gaming channel ID: %s", os.getenv("DSCRD_CHNL_GAMING"))
    #     logger.debug(
    #         "Discord gaming channel: %s",
    #         self.discord_bot.get_channel(int(os.getenv("DSCRD_CHNL_GAMING"))),
    #     )
    #     discord_gaming_chnl = self.discord_bot.get_channel(
    #         int(os.getenv("DSCRD_CHNL_GAMING"))
    #     )
    #     await ctx.send("Hai there!")
    #     await discord_gaming_chnl.send("oh hai there, discord")

    def callback_whisper(self, uuid: UUID, data: dict) -> None:
        print("got callback for UUID " + str(uuid))
        pprint(data)

    def init_channel_state(self, channels):
        channel_states = {}
        for channel in channels:
            channel_states[channel] = {
                "started_at": datetime.strptime("1970-01-01", "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                ),
            }
        return channel_states

    def formatStreamEmbed(self, stream):
        embed = discord.Embed(
            title=f"{stream.user.display_name} is Live on Twitch!",
            description=stream.title,
            color=0x9D2235,
        )
        embed.add_field(name="Streaming", value=stream.game_name)
        embed.add_field(
            name="Started at",
            value=fmt_datetime_to_minute(
                naive_to_us_central(stream.started_at),
            ),
        )
        embed.set_image(url=stream.user.profile_image)
        return embed

    def formatUserInfoEmbed(self, userdata):
        embed = discord.Embed(
            title=f"Twitch User Info for {userdata.display_name}",
            description=userdata.description,
        )
        embed.add_field(name="Total views", value=userdata.view_count),
        embed.set_image(url=userdata.profile_image)
        return embed

    def formatFollowerInfoEmbed(self, user, image_url, follower_list):
        embed = discord.Embed(title=f"Twitch followers for {user}")
        embed.set_image(url=image_url)
        embed.add_field(name="Follower Count", value=len(follower_list)),
        embed.add_field(name="Follower List", value=follower_list, inline=False)
        embed.set_image(url=image_url)
        return embed

    def parseFollowers(self, response):
        follower_list = []
        for follower in response:
            follower_list.append(follower["from_name"])
        return follower_list

    async def info_from_name(self, username):
        response = await self.client.fetch_users(username)
        return response[0].id, response[0].profile_image

    async def get_user_data(self, users: List[str] = None):
        if not users:
            users = self.join_channels_list
        return self.twitch_client.fetch_users(users)

    async def get_live_channels(self, query: str = "e"):
        return await self.twitch_client.search_channels(query, live_only=True)

    async def get_stream_data(self, channels):
        return await self.twitch_client.fetch_streams(user_logins=channels)
