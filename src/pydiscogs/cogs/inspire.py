import json
import logging

import aiohttp
from discord.ext import commands

logger = logging.getLogger(__name__)


class InspireQuote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # bot.slash_command(guild_ids=guild_ids)(self.inspire)

    @commands.slash_command()
    async def inspire(self, ctx):
        await ctx.respond(await self.get_quote())

    async def get_quote(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://zenquotes.io/api/random") as r:
                if r.status == 200:
                    json_data = json.loads(await r.text())
                    quote = json_data[0]["q"] + " -" + json_data[0]["a"]
                    return quote
