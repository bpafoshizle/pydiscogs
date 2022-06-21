import logging
from datetime import datetime
from typing import List

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

# from icecream import ic
from pydiscogs.utils.timing import calc_tomorrow_7am, wait_until

logger = logging.getLogger(__name__)


class StockQuote(commands.Cog):
    def __init__(
        self,
        bot,
        stock_list: List[str],
        polygon_token,
        discord_post_channel_id,
    ):
        self.bot = bot
        self.stock_list = stock_list
        self.polygon_token = polygon_token
        self.discord_post_channel_id = discord_post_channel_id

        # pylint: disable=no-member
        self.stock_morning_report_task.start()

        # bot.slash_command(guild_ids=guild_ids)(self.stockquote)
        # bot.slash_command(guild_ids=guild_ids)(self.stockclose)
        # bot.slash_command(guild_ids=guild_ids)(self.stocknews)
        # bot.slash_command(guild_ids=guild_ids)(self.marketnews)

    @commands.slash_command()
    async def stockquote(self, ctx, symbol):
        stock_quote = self.formatLatestStockQuoteEmbed(
            *await self.getLatestStockQuote(symbol)
        )
        await ctx.respond(embed=stock_quote)

    @commands.slash_command()
    async def stockclose(self, ctx, symbol):
        stock_close = self.formatPrevCloseEmbed(
            *await self.getPrevClose(symbol.upper())
        )
        await ctx.respond(embed=stock_close)

    @commands.slash_command()
    async def stocknews(self, ctx, symbol):
        stock_news = self.formatStockNewsEmbed(
            await self.getStockNewsMarketWatch(symbol)
        )
        for article in stock_news:
            logger.debug(article)
            await ctx.respond(embed=article)

    @commands.slash_command()
    async def marketnews(self, ctx):
        stock_news = self.formatStockNewsEmbed(await self.getLatestMarketWatch())
        for article in stock_news:
            logger.debug(article)
            await ctx.respond(embed=article)

    @tasks.loop(hours=24)
    async def stock_morning_report_task(self):
        logger.info("channel id %s", self.discord_post_channel_id)
        chnl = self.bot.get_channel(int(self.discord_post_channel_id))
        logger.info("Got channel %s", chnl)
        stock_news = self.formatStockNewsEmbed(await self.getLatestMarketWatch())
        for article in stock_news:
            logger.debug(article)
            await chnl.send(embed=article)

    @stock_morning_report_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        logger.info("stock_morning_report_task.before_loop: bot ready")
        tmrw_7am = calc_tomorrow_7am()
        logger.info(
            "stock_morning_report_task.before_loop: waiting until: %s", tmrw_7am
        )
        await wait_until(tmrw_7am)
        logger.info("stock_morning_report_task.before_loop: waited until 7am")

    async def getStockNewsPolygon(self, symbol):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.polygon.io/v1/meta/symbols/{symbol}/news?perpage=5&page=1&apiKey={self.polygon_token}"
            ) as r:
                if r.status == 200:
                    news = await r.json()
                    logger.debug(news)
                    return news

    async def getLatestMarketWatch(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.marketwatch.com/latest-news?mod=top_nav"
            ) as r:
                if r.status == 200:
                    return self.parseMarketWatch(await r.text())

    async def getStockNewsMarketWatch(self, symbol):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.marketwatch.com/investing/stock/{symbol}?mod=quote_search"
            ) as r:
                if r.status == 200:
                    return self.parseMarketWatch(await r.text())

    def parseMarketWatch(self, responseText):
        soup = BeautifulSoup(responseText, features="html.parser")
        soup = soup.find(
            "div", attrs={"class": ["collection__elements", "j-scrollElement"]}
        )
        soup = soup.find_all("div", attrs={"class": ["element--article"]})[:5]
        news = []
        for section in soup:
            article = {}
            article["timestamp"] = getattr(
                section.find("span", class_="article__timestamp"),
                "string",
                datetime.now(),
            )
            article["source"] = getattr(
                section.find("span", class_="article__author"), "string", "by Unknown"
            )
            if "no-image" not in section["class"]:
                article["image"] = (
                    section.find("a", class_="figure__image")
                    .img["data-srcset"]
                    .split(",")[2]
                    .split()[0]
                )
                # article["url"] = section.find("a", class_="figure__image")["href"]
            try:
                article["title"] = section.find(
                    "h3", class_="article__headline"
                ).a.string.strip()
                article["url"] = section.find("h3", class_="article__headline").a[
                    "href"
                ]
            except AttributeError:
                try:
                    article["title"] = section.find(
                        "h3", class_="article__headline"
                    ).span.string.strip()
                except AttributeError:
                    article["title"] = "No title found"
                    logger.info(
                        "No article__headline in no-image class element. Section: %s",
                        section,
                    )

            news.append(article)
        return news

    async def getPrevClose(self, symbol):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?unadjusted=true&apiKey={self.polygon_token}"
            ) as r:
                if r.status == 200:
                    json_data = await r.json()
                    # ic(json_data)
                    logger.debug(json_data)
                    prev_close = json_data["results"][0]["c"]
                    prev_high = json_data["results"][0]["h"]
                    prev_low = json_data["results"][0]["l"]
                    return (symbol, prev_close, prev_high, prev_low)

    async def getLatestStockQuote(self, symbol):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://finance.yahoo.com/quote/{symbol}?p={symbol}"
            ) as r:
                if r.status == 200:
                    logger.debug(
                        f"received response from https://finance.yahoo.com/quote/{symbol}?p={symbol}"
                    )
                    soup = BeautifulSoup(await r.text(), features="html.parser")
                    soup = soup.find(id="quote-header-info")
                    name = soup.h1.text
                    lastprice = soup.find(
                        "fin-streamer", attrs={"data-field": "regularMarketPrice"}
                    )["value"]
                    change = soup.find(
                        "fin-streamer", attrs={"data-field": "regularMarketChange"}
                    )["value"]
                    pctchange = soup.find(
                        "fin-streamer",
                        attrs={"data-field": "regularMarketChangePercent"},
                    )["value"]
                    quotetime = soup.find("div", id="quote-market-notice").string

                    return (symbol, name, lastprice, change, pctchange, quotetime)

    def formatLatestStockQuoteEmbed(
        self, symbol, name, lastprice, change, pctchange, quotetime
    ):
        embed = discord.Embed(
            title="Stock Latest Quote",
            description="Most recent quote from your friendly Egroup bot",
            color=0x9D2235,
        )
        embed.add_field(name="Symbol", value=symbol)
        embed.add_field(name="Name", value=name)
        embed.add_field(name="Quote time", value=quotetime, inline=False)
        embed.add_field(name="Last Price", value=lastprice)
        embed.add_field(name="Change", value=change)
        embed.add_field(name="% Change", value=pctchange)
        return embed

    def formatPrevCloseEmbed(self, symbol, prev_close, prev_high, prev_low):
        embed = discord.Embed(
            title="Stock Previous Close",
            description="Previous close info from your friendly Egroup bot",
            color=0x9D2235,
        )
        embed.add_field(name="Symbol", value=symbol, inline=False)
        embed.add_field(name="Close", value=prev_close)
        embed.add_field(name="High", value=prev_high)
        embed.add_field(name="Low", value=prev_low)
        return embed

    def formatStockNewsEmbed(self, news):
        embeds = []
        for article in news:
            embed = discord.Embed(
                title=article["title"], url=article.get("url", ""), color=0x9D2235
            )
            embed.set_image(url=article.get("image", ""))
            embed.add_field(name="Source", value=article["source"])
            embed.add_field(
                name="Timestamp", value=article.get("timestamp", datetime.now())
            )
            embeds.append(embed)
        return embeds
