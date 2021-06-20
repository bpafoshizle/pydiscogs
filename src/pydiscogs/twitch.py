import logging
import os
from datetime import datetime

import discord
import twitchio as twio
from cogs.utils.timing import fmt_datetime_to_minute, naive_to_us_central
from discord.ext import commands, tasks
from twitchio.ext import commands as twitch_commands

logger = logging.getLogger(__name__)

join_channels = [
    "bpafoshizle",
    "ephenry84",
    "elzblazin",
    "kuhouseii",
]

followed_channels = [
    "JackFrags",
    "TrueGameDataLive",
    "Stodeh",
    "Jukeyz",
    "Symfuhny",
    "NICKMERCS",
]


class Twitch(commands.Cog):
    def __init__(self, bot):
        self.channel_states = self.init_channel_state(join_channels + followed_channels)
        self.discord_bot = bot
        self.client = twio.Client(
            client_id=os.getenv("TWITCH_BOT_CLIENT_ID"),
            client_secret=os.getenv("TWITCH_BOT_CLIENT_SECRET"),
        )
        self.bot = twitch_commands.Bot(
            # set up the bot
            irc_token=os.getenv("TWITCH_CHAT_OAUTH_TOKEN"),
            client_id=os.getenv("TWITCH_BOT_CLIENT_ID"),
            nick=os.getenv("TWITCH_BOT_USERNAME"),
            prefix="!",
            initial_channels=join_channels,
        )

        self.discord_bot.loop.create_task(self.bot.start())
        # pylint: disable=no-member
        self.check_channels_live_task.start()

        self.bot.listen("event_ready")(self.event_ready)
        self.bot.listen("event_message")(self.event_message)
        self.bot.listen("event_userstate")(self.event_userstate)
        self.bot.listen("event_webhook")(self.event_webhook)
        self.bot.command(name="sayhello")(self.sayhello)

    # TwitchIO event handlers
    async def event_message(self, ctx):
        logger.debug(ctx.content)
        # make sure the bot ignores itself and the streamer
        if ctx.author.name.lower() == os.environ["TWITCH_BOT_USERNAME"].lower():
            return
        await self.bot.handle_commands(ctx)

    async def event_ready(self):
        logger.info("Logged into Twitch %s", self.bot.nick)

    async def event_userstate(self, user):
        logger.info("event_userstate: %s", user)

    async def event_webhook(self, data):
        logger.info("event_webhook: %s", data)

    # Discord tasks and commands
    @tasks.loop(minutes=1)
    async def check_channels_live_task(self):
        logger.debug("channel id %s", os.getenv("DSCRD_CHNL_GAMING"))
        chnl = self.discord_bot.get_channel(int(os.getenv("DSCRD_CHNL_GAMING")))
        logger.debug("Got channel %s", chnl)
        response = await self.client.get_streams(
            channels=join_channels + followed_channels
        )
        for liveuserdata in response:
            logger.debug(liveuserdata)
            userdata_user_name = liveuserdata["user_name"]
            userdata_started_at = datetime.strptime(
                liveuserdata["started_at"], "%Y-%m-%dT%H:%M:%SZ"
            )
            if (
                self.channel_states[userdata_user_name]["started_at"]
                < userdata_started_at
            ):
                self.channel_states[userdata_user_name][
                    "started_at"
                ] = userdata_started_at
                profileuserdata = await self.client.get_users(liveuserdata["user_id"])
                logger.info(profileuserdata)
                await chnl.send(
                    embed=self.formatUserLiveEmbed(liveuserdata, profileuserdata[0])
                )
            else:
                logger.info(
                    "User %s still streaming since %s",
                    userdata_user_name,
                    self.channel_states[userdata_user_name]["started_at"],
                )

    @check_channels_live_task.before_loop
    async def before(self):
        await self.discord_bot.wait_until_ready()
        logger.info("check_channels_live_task.before_loop: bot ready")

    @commands.command()
    async def twitch_checklive(self, ctx, channel=None):
        channels = join_channels + followed_channels
        if channel:
            channels = [channel]
        response = await self.client.get_streams(channels=channels)
        logger.debug(response)
        for liveuserdata in response:
            profileuserdata = await self.client.get_users(liveuserdata["user_id"])
            logger.info(profileuserdata)
            await ctx.send(
                embed=self.formatUserLiveEmbed(liveuserdata, profileuserdata[0])
            )

    @commands.command()
    async def twitch_getuser(self, ctx, user):
        response = await self.client.get_users(user)
        logger.debug(response)
        await ctx.send(embed=self.formatUserInfoEmbed(response[0]))

    @commands.command()
    async def twitch_getfollowers(self, ctx, username):
        userid, image_url = await self.info_from_name(username)
        response = await self.client.get_followers(int(userid))
        embed = self.formatFollowerInfoEmbed(
            username, image_url, self.parseFollowers(response)
        )
        logger.debug(response)
        await ctx.send(embed=embed)

    # TwitchIO command
    async def sayhello(self, ctx):
        logger.debug("Discord gaming channel ID: %s", os.getenv("DSCRD_CHNL_GAMING"))
        logger.debug(
            "Discord gaming channel: %s",
            self.discord_bot.get_channel(int(os.getenv("DSCRD_CHNL_GAMING"))),
        )
        discord_gaming_chnl = self.discord_bot.get_channel(
            int(os.getenv("DSCRD_CHNL_GAMING"))
        )
        await ctx.send("Hai there!")
        await discord_gaming_chnl.send("oh hai there, discord")

    def init_channel_state(self, followed_channels):
        channel_states = {}
        for channel in followed_channels:
            channel_states[channel] = {
                "started_at": datetime.strptime("1970-01-01", "%Y-%m-%d")
            }
        return channel_states

    def formatUserLiveEmbed(self, liveuserdata, profileuserdata):
        embed = discord.Embed(
            title=f"{liveuserdata['user_name']} is Live on Twitch!",
            description=liveuserdata["title"],
            color=0x9D2235,
        )
        embed.add_field(name="Streaming", value=liveuserdata["game_name"])
        embed.add_field(
            name="Started at",
            value=fmt_datetime_to_minute(
                naive_to_us_central(
                    datetime.strptime(liveuserdata["started_at"], "%Y-%m-%dT%H:%M:%SZ")
                ),
            ),
        )
        embed.set_image(url=profileuserdata.profile_image)
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
        response = await self.client.get_users(username)
        return response[0].id, response[0].profile_image
