import logging
import os
from datetime import datetime
from typing import List

import discord
import yfinance as yf
from discord.ext import commands, tasks
from polygon import RESTClient

# from icecream import ic
from pydiscogs.utils.timing import calc_tomorrow_7am, wait_until

logger = logging.getLogger(__name__)


class StockQuote(commands.Cog):
    def __init__(
        self,
        bot,
        stock_list: List[str],
        polygon_api_key: str = os.getenv("POLYGON_API_KEY"),
        discord_post_channel_id = None,
    ):
        
        if polygon_api_key is None:
            raise ValueError(
                f"Must specify env var POLYGON_API_KEY or pass api_key in constructor"
            )
        if discord_post_channel_id is None:
            raise ValueError(
                f"Must specify env var DISCORD_POST_CHANNEL_ID or pass channel_id in constructor"
            )
        self.bot = bot
        self.stock_list = stock_list
        self.discord_post_channel_id = discord_post_channel_id
        self.polygon_client = RESTClient(api_key=polygon_api_key)

        # pylint: disable=no-member
        self.stock_morning_report_task.start()

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
        stock_news = self.formatStockNewsEmbed(await self.getStockNewsyfinance(symbol))
        for article in stock_news:
            logger.debug(article)
            await ctx.respond(embed=article)

    @commands.slash_command()
    async def getlateststocknews(self, ctx):
        stock_news = self.formatStockNewsEmbed(await self.getLatestNewsStockList())
        for article in stock_news:
            logger.debug(article)
            await ctx.respond(embed=article)

    @tasks.loop(hours=24)
    async def stock_morning_report_task(self):
        logger.info("channel id %s", self.discord_post_channel_id)
        chnl = self.bot.get_channel(int(self.discord_post_channel_id))
        logger.info("Got channel %s", chnl)
        stock_news = self.formatStockNewsEmbed(await self.getLatestNewsStockList())
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

    async def getStockNewsyfinance(self, symbol, maxcount=5):
        ticker = yf.Ticker(symbol)
        return ticker.news[:maxcount]

    async def getLatestNewsStockList(self):
        stock_news = []
        for stock in self.stock_list:
            try:
                stock_news.append((await self.getStockNewsyfinance(stock, 1))[0])
            except IndexError:
                pass
        return stock_news

    async def getPrevClose(self, symbol):
        prevClose = self.polygon_client.get_previous_close_agg(symbol)[0]
        logger.debug(prevClose)
        return (prevClose.ticker, prevClose.close, prevClose.high, prevClose.low)

    async def getLatestStockQuote(self, symbol):
        ticker = yf.Ticker(symbol)
        # print all attributes and values of fast_info

        if ticker.fast_info.previous_close is not None:
            change = ticker.fast_info.last_price - ticker.fast_info.previous_close
            pctchange = change / ticker.fast_info.previous_close * 100
        else:
            change = 0
            pctchange = 0

        # Safely handle missing 'Earnings Date' in the 'calendar' dictionary
        try:
            earnings_date = ticker.calendar["Earnings Date"][0]
        except (KeyError, IndexError):
            earnings_date = "N/A"

        return (
            ticker.info.get("symbol", "N/A"),
            ticker.info.get("shortName", "N/A"),
            (
                str(round(ticker.fast_info.last_price, 2))
                if hasattr(ticker.fast_info, "last_price")
                else "N/A"
            ),
            str(round(change, 2)) if isinstance(change, (int, float)) else "N/A",
            str(round(pctchange, 2)) if isinstance(pctchange, (int, float)) else "N/A",
            str(datetime.now()),
            earnings_date,
        )

    def formatLatestStockQuoteEmbed(
        self, symbol, name, lastprice, change, pctchange, quotetime, earningsdate
    ):
        embed = discord.Embed(
            title="Stock Latest Quote",
            description="Most recent quote from your stock bot",
            color=0x9D2235,
        )
        embed.add_field(name="Symbol", value=symbol)
        embed.add_field(name="Name", value=name)
        embed.add_field(name="Quote time", value=quotetime, inline=False)
        embed.add_field(name="Last Price", value=lastprice)
        embed.add_field(name="Change", value=change)
        embed.add_field(name="% Change", value=pctchange)
        embed.add_field(name="Earnings Date", value=earningsdate)
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
                title=article["title"], url=article.get("link", ""), color=0x9D2235
            )
            try:
                thumbnail = article.get("thumbnail", {})
                resolutions = thumbnail.get("resolutions", [{}])
                url = resolutions and resolutions[0].get("url", "")
                embed.set_image(url=url)
            except (KeyError, IndexError, AttributeError) as e:
                logger.debug("Error setting image: %s", e)
                embed.set_image(url="")
            embed.add_field(name="Source", value=article["publisher"])
            embed.add_field(
                name="Timestamp",
                value=datetime.fromtimestamp(
                    article.get("providerPublishTime", datetime.now().timestamp())
                ).strftime("%Y-%m-%d %H:%M:%S"),
            )
            embeds.append(embed)
        return embeds
