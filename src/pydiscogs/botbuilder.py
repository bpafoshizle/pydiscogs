import logging
import os

from discord.ext import commands
from pyaml_env import parse_config

from pydiscogs.cogs.inspire import InspireQuote
from pydiscogs.cogs.reddit import Reddit
from pydiscogs.cogs.stocks import StockQuote
from pydiscogs.cogs.twitch import Twitch
from pydiscogs.cogs.wotd import WordOfTheDay

LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
logging.basicConfig(level=LOGLEVEL)


def build_bot(yaml_config="./tests/testbot.yaml"):
    config = parse_config(yaml_config)
    command_prefix = config.get("commandPrefix")
    assert command_prefix, "commandPrefix is a required configuration value"
    bot = commands.Bot(command_prefix=config["commandPrefix"])

    guild_ids = config.get("guildIds")
    assert guild_ids, "guildIds is a required configuration value"

    discord_token = config["discordToken"]
    assert discord_token, "discordToken is a required configuration value"

    async def on_ready():
        logging.info("Logged in as %s", bot.user)

    async def hello(ctx, name: str = None):
        name = name or ctx.author.name
        await ctx.respond(f"Hello {name}!")

    bot.add_listener(on_ready)
    bot.slash_command(guild_ids=guild_ids)(hello)

    for cog in config["cogs"]:
        cog_name = cog["name"]
        cog_properties = cog.get("properties")
        if cog_name == "inspire":
            add_inspire_cog(bot, guild_ids)
        elif cog_name == "wotd":
            add_wotd_cog(bot, guild_ids, cog_properties)
        elif cog_name == "stocks":
            add_stocks_cog(bot, guild_ids, cog_properties)
        elif cog_name == "twitch":
            add_twitch_cog(bot, guild_ids, cog_properties)
        elif cog_name == "reddit":
            add_reddit_cog(bot, guild_ids, cog_properties)

    bot.discord_token = discord_token
    # logging.info("running bot: %s", bot)
    # bot.run(discord_token)

    return bot


def check_and_get_property(cog_properties, cog_name, property_name):
    property_value = cog_properties.get(property_name)
    assert (
        property_value
    ), f"{property_name} is a required configuration for {cog_name} cog"
    return property_value


def add_inspire_cog(bot, guild_ids):
    bot.add_cog(InspireQuote(bot, guild_ids))


def add_wotd_cog(bot, guild_ids, cog_properties):
    post_channel_id = check_and_get_property(cog_properties, "wotd", "postChannelId")
    bot.add_cog(WordOfTheDay(bot, guild_ids, post_channel_id))


def add_stocks_cog(bot, guild_ids, cog_properties):
    post_channel_id = check_and_get_property(cog_properties, "stocks", "postChannelId")
    polygon_token = check_and_get_property(cog_properties, "stocks", "polygonToken")
    stock_list = check_and_get_property(cog_properties, "stocks", "stockList")
    bot.add_cog(StockQuote(bot, guild_ids, stock_list, polygon_token, post_channel_id))


def add_twitch_cog(bot, guild_ids, cog_properties):
    post_channel_id = check_and_get_property(cog_properties, "twitch", "postChannelId")
    twitch_client_id = check_and_get_property(
        cog_properties, "twitch", "twitchClientID"
    )
    twitch_client_secret = check_and_get_property(
        cog_properties, "twitch", "twitchClientSecret"
    )
    join_channel_list = check_and_get_property(
        cog_properties, "twitch", "joinChannelList"
    )
    bot.add_cog(
        Twitch(
            bot,
            guild_ids,
            twitch_client_id,
            twitch_client_secret,
            post_channel_id,
            join_channel_list,
        )
    )


def add_reddit_cog(bot, guild_ids, cog_properties):
    post_channel_id = check_and_get_property(cog_properties, "reddit", "postChannelId")
    reddit_client = check_and_get_property(cog_properties, "reddit", "redditClient")
    reddit_secret = check_and_get_property(cog_properties, "reddit", "redditSecret")
    reddit_username = check_and_get_property(cog_properties, "reddit", "redditUsername")
    reddit_password = check_and_get_property(cog_properties, "reddit", "redditPassword")
    subreddit_list = check_and_get_property(cog_properties, "reddit", "subRedditList")
    gfycat_client = check_and_get_property(cog_properties, "reddit", "gfycatClientId")
    gfycat_client_secret = check_and_get_property(
        cog_properties, "reddit", "gfycatClientSecret"
    )
    bot.add_cog(
        Reddit(
            bot,
            guild_ids,
            reddit_client,
            reddit_secret,
            reddit_username,
            reddit_password,
            subreddit_list,
            gfycat_client,
            gfycat_client_secret,
            post_channel_id,
        )
    )
