import logging
import os

import asyncpraw
import discord
from cogs.utils.timing import calc_tomorrow_6am, wait_until
from discord.ext import commands, tasks
from gfycat.client import GfycatClient

logger = logging.getLogger(__name__)


class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # pylint: disable=no-member
        self.morning_hottie_task.start()
        self.reddit = asyncpraw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent="asyncpraw script by u/egroup-bot",
        )
        self.gfycat = GfycatClient(
            os.getenv("GFYCAT_CLIENT_ID"), os.getenv("GFYCAT_CLIENT_SECRET")
        )

    @commands.command()
    async def reddit_hottie(self, ctx):
        hotties = await self.getHottie()
        for hottie in hotties:
            logger.debug(hottie)
            await ctx.send(embed=hottie)

    @tasks.loop(hours=24)
    async def morning_hottie_task(self):
        logger.debug("channel id %s", os.getenv("DSCRD_CHNL_GENERAL"))
        chnl = self.bot.get_channel(int(os.getenv("DSCRD_CHNL_GENERAL")))
        logger.debug("Got channel %s", chnl)
        hotties = await self.getHottie()
        for hottie in hotties:
            logger.debug(hottie)
            await chnl.send(embed=hottie)

    @morning_hottie_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        logger.info("morning_hottie_task.before_loop: bot ready")
        tmrw_6am = calc_tomorrow_6am()
        logger.info(
            "morning_hottie_task.before_loop: waiting until: %s",
            tmrw_6am,
        )
        await wait_until(tmrw_6am)
        logger.info("morning_hottie_task.before_loop: waited until 7am")

    async def getHottie(self):
        subreddit = await self.reddit.subreddit("sexygirls")
        submissions = subreddit.hot(limit=1)
        return await self.formatEmbed(submissions)

    def handleHottieImageUrl(self, url):
        if "gfycat" in url:
            return self.getGfyCatGifUrl(url.rsplit("/", 1)[-1])
        else:
            return url

    def getGfyCatGifUrl(self, gfyid):
        response = self.gfycat.query_gfy(gfyid)
        return response["gfyItem"]["content_urls"]["max5mbGif"]["url"]

    async def formatEmbed(self, submissions):
        embeds = []
        async for submission in submissions:
            embed = discord.Embed(
                title="A Lady",
                url=f"https://www.reddit.com{submission.permalink}",
                color=0x9D2235,
            )
            embed.set_image(url=self.handleHottieImageUrl(submission.url))
            logger.info("URL: %s", submission.url)
            embed.add_field(name="Name", value=submission.title)
            embeds.append(embed)
        return embeds
