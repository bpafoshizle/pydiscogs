import logging
import os
from datetime import datetime

import aiohttp
import discord
from bs4 import BeautifulSoup
from cogs.utils.timing import calc_tomorrow_7am, wait_until
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)


class SeekingAlhpaNews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # pylint: disable=no-member
        self.morning_report_task.start()

    @commands.command()
    async def alphanews(self, ctx, symbol=None):
        if symbol:
            # sa_news = self.formatSeekingAlphaNewsEmbed(await self.getStockNews(symbol))
            pass
        else:
            sa_news = self.formatSeekingAlphaNewsEmbed(await self.getMarketNews())

        for article in sa_news:
            logger.debug(article)
            await ctx.send(embed=article)

    @tasks.loop(hours=24)
    async def morning_report_task(self):
        logger.debug("channel id %s", os.getenv("DSCRD_CHNL_MONEY"))
        chnl = self.bot.get_channel(int(os.getenv("DSCRD_CHNL_MONEY")))
        logger.debug("Got channel %s", chnl)
        stock_news = self.formatSeekingAlphaNewsEmbed(await self.getMarketNews())
        for article in stock_news:
            logger.debug(article)
            await chnl.send(embed=article)

    @morning_report_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        logger.info("seeking_alpha_morning_report_task.before_loop: bot ready")
        tmrw_7am = calc_tomorrow_7am()
        logger.info(
            "seeking_alpha_morning_report_task.before_loop: waiting until: %s",
            tmrw_7am,
        )
        await wait_until(tmrw_7am)
        logger.info("seeking_alpha_morning_report_task.before_loop: waited until 7am")

    async def getMarketNews(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://seekingalpha.com/market-news/all") as r:
                if r.status == 200:
                    return self.parseMarketNews(await r.text())

    async def getStockNews(self, symbol):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://seekingalpha.com/symbol/{symbol}/news"
            ) as r:
                if r.status == 200:
                    return self.parseMarketWatch(await r.text())

    def parseMarketNews(self, responseText):
        soup = BeautifulSoup(responseText, features="html.parser")
        soup = soup.select("li[class='mc']")[:5]
        news = []
        for section in soup:
            article = {}
            article["timestamp"] = getattr(
                section.find("span", class_="item-date"),
                "string",
                datetime.now(),
            )
            article["source"] = "Seeking Alpha"
            article["title"] = section.find("div", class_="title").a.string
            article[
                "image"
            ] = "https://seekingalpha.com/samw/static/images/OrganizationLogo.7f745bcc.png"
            article["url"] = (
                "https://seekingalpha.com/"
                + section.find("div", class_="title").a["href"]
            )
            news.append(article)
        return news

    def formatSeekingAlphaNewsEmbed(self, news):
        embeds = []
        for article in news:
            embed = discord.Embed(
                title=article["title"],
                url=article.get("url", ""),
                color=0x9D2235,
            )
            embed.set_image(url=article.get("image", ""))
            embed.add_field(name="Source", value=article["source"])
            embed.add_field(
                name="Timestamp", value=article.get("timestamp", datetime.now())
            )
            embeds.append(embed)
        return embeds
