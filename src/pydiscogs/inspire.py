import json

import aiohttp
from discord.ext import commands

from pydiscogs.utils.decorator_override import pydiscog_slash_command


class InspireQuote(commands.Cog):
    def __init__(self, bot, guild_ids=None):
        self.bot = bot
        bot.slash_command(guild_ids=guild_ids)(self.inspire)

    async def inspire(self, ctx):
        await ctx.respond(await self.get_quote())

    async def get_quote(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://zenquotes.io/api/random") as r:
                if r.status == 200:
                    json_data = json.loads(await r.text())
                    quote = json_data[0]["q"] + " -" + json_data[0]["a"]
                    return quote
