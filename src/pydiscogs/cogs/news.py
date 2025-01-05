import logging

import discord
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

class News(commands.Cog):
    def __init__(self, bot, discord_post_channel_id):
        self.bot = bot
        self.discord_post_channel_id = discord_post_channel_id
    
    @commands.slash_command()
    async def news(self, ctx: commands.Context):
        await ctx.respond("News command is currently under development.")