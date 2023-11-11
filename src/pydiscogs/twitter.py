import logging

# import discord
import tweepy
# from discord.ext import commands, tasks
from discord.ext import commands

logger = logging.getLogger(__name__)


class Twitter(commands.Cog):
    def __init__(
        self,
        bot,
        guild_ids,
        twitter_bearer_token,
        twitter_handle,
        discord_post_channel_id: int,
    ):
        self.bot = bot
        # pylint: disable=no-member
        self.morning_posts_task.start()
        self.twitter_handle = twitter_handle
        self.discord_post_channel_id = discord_post_channel_id
        self.twitter = tweepy.asynchronous.AsyncClient(
            auth=tweepy.OAuth2BearerHandler(twitter_bearer_token),
            wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True,
        )

        bot.slash_command(guild_ids=guild_ids)(self.twitter_search)

    async def twitter_search(self, ctx, search_term):
        tweets = self.twitter.search_recent_tweets(search_term, max_results=5)
        await ctx.respond(tweets)
