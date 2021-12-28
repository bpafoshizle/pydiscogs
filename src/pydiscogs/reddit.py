import logging

import asyncpraw
import discord
from discord.ext import commands, tasks
from gfycat.client import GfycatClient

from pydiscogs.utils.timing import calc_tomorrow_6am, wait_until

# from icecream import ic


logger = logging.getLogger(__name__)


class Reddit(commands.Cog):
    def __init__(
        self,
        bot,
        reddit_client_id,
        reddit_client_secret,
        reddit_username,
        reddit_password,
        subreddit_list,
        gfycat_client_id,
        gfycat_client_secret,
        discord_post_channel_id: int,
    ):
        self.bot = bot
        # pylint: disable=no-member
        self.morning_posts_task.start()
        self.reddit = asyncpraw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            username=reddit_username,
            password=reddit_password,
            user_agent="pydiscogs reddit cog",
        )
        self.gfycat = GfycatClient(gfycat_client_id, gfycat_client_secret)
        self.subreddit_list = subreddit_list
        self.discord_post_channel_id = discord_post_channel_id

    @commands.command()
    async def reddit_post(self, ctx, subreddit: str, limit: int = 1):
        posts = await self.getTopEntries(subreddit=subreddit, limit=limit)
        for post in posts:
            logger.debug(post)
            await ctx.send(embed=post)

    @commands.command()
    async def reddit_post_id(self, ctx, postId):
        sub = await self.reddit.submission(id=postId)
        post = self.formatEmbed(sub)
        logger.debug(post)
        await ctx.send(embed=post)

    @tasks.loop(hours=24)
    async def morning_posts_task(self):
        logger.debug("channel id %s", self.discord_post_channel_id)
        chnl = self.bot.get_channel(int(self.discord_post_channel_id))
        logger.debug("Got channel %s", chnl)
        for subreddit in self.subreddit_list:
            posts = await self.getTopEntry(subreddit)
            for post in posts:
                logger.debug(post)
                await chnl.send(embed=post)

    @morning_posts_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        logger.info("morning_posts_task.before_loop: bot ready")
        tmrw_6am = calc_tomorrow_6am()
        logger.info(
            "morning_posts_task.before_loop: waiting until: %s",
            tmrw_6am,
        )
        await wait_until(tmrw_6am)
        logger.info("morning_posts_task.before_loop: waited until 7am")

    async def getTopEntry(self, subreddit):
        return await self.getTopEntries(subreddit, 1)

    async def getTopEntries(self, subreddit, limit):
        subreddit = await self.reddit.subreddit(subreddit)
        submissions = []
        async for submission in subreddit.hot():  # use .new.stream() for endless polling
            if submission.stickied:
                continue
            submissions.append(submission)
            if len(submissions) == limit:
                break
        return await self.formatEmbedList(submissions)

    def handlePostImageUrl(self, sub):
        imageExtTuple = (".jpg", ".jpeg", ".png", ".gif", ".gifv", ".webm", ".mp4")
        if "gfycat" in sub.url:
            return self.getGfyCatGifUrl(sub.url.rsplit("/", 1)[-1])
        elif sub.url.lower().endswith(imageExtTuple):
            return sub.url
        else:
            try:
                return sub.preview["images"][0]["source"]["url"]
            except KeyError:
                return "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=400&q=80"

    def getGfyCatGifUrl(self, gfyid):
        response = self.gfycat.query_gfy(gfyid)
        return response["gfyItem"]["content_urls"]["max5mbGif"]["url"]

    async def formatEmbedList(self, submissions):
        embeds = []
        for submission in submissions:
            await submission.subreddit.load()
            # ic(submission.subreddit)
            embeds.append(self.formatEmbed(submission))
        return embeds

    def formatEmbed(self, submission):
        embed = discord.Embed(
            title=f"Top hot entry from {submission.subreddit.display_name}",
            url=f"https://www.reddit.com{submission.permalink}",
            color=0x9D2235,
        )
        embed.set_image(url=self.handlePostImageUrl(submission))
        logger.info("URL: %s", submission.url)
        embed.add_field(name="Name", value=submission.title)
        return embed
