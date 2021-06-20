import json

import aiohttp
from discord.ext import commands


class InspireQuote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def inspire(self, ctx):
        await ctx.send(await self.get_quote())

    async def get_quote(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://zenquotes.io/api/random") as r:
                if r.status == 200:
                    json_data = json.loads(await r.text())
                    quote = json_data[0]["q"] + " -" + json_data[0]["a"]
                    return quote
