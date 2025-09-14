import logging
import os

import discord
from discord.ext import commands
from pyaml_env import parse_config

from pydiscogs.cogs.ai import AI
from pydiscogs.cogs.inspire import InspireQuote
from pydiscogs.cogs.reddit import Reddit
from pydiscogs.cogs.stocks import StockQuote
from pydiscogs.cogs.twitch import Twitch
from pydiscogs.cogs.wotd import WordOfTheDay

LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
logging.basicConfig(level=LOGLEVEL)


def build_bot(yaml_config="./tests/testbot.yaml"):

    intents = discord.Intents.default()
    intents.message_content = (
        True  # < This may give you `read-only` warning, just ignore it.
    )
    # This intent requires "Message Content Intent" to be enabled at https://discord.com/developers

    config = parse_config(yaml_config)
    command_prefix = config.get("commandPrefix")
    assert command_prefix, "commandPrefix is a required configuration value"
    guild_ids = config.get("guildIds")
    assert guild_ids, "guildIds is a required configuration value"

    bot = commands.Bot(
        command_prefix=config["commandPrefix"], debug_guilds=guild_ids, intents=intents
    )

    discord_token = config["discordToken"]
    assert discord_token, "discordToken is a required configuration value"

    async def on_ready():
        logging.info("Logged in as %s", bot.user)

    bot.add_listener(on_ready)
    # bot.slash_command(guild_ids=guild_ids)(hello)

    for cog in config["cogs"]:
        cog_name = cog["name"]
        cog_properties = cog.get("properties")
        if cog_name == "inspire":
            add_inspire_cog(bot)
        elif cog_name == "wotd":
            add_wotd_cog(bot, cog_properties)
        elif cog_name == "stocks":
            add_stocks_cog(bot, cog_properties)
        elif cog_name == "twitch":
            add_twitch_cog(bot, cog_properties)
        elif cog_name == "reddit":
            add_reddit_cog(bot, cog_properties)
        elif cog_name == "ai":
            add_ai_cog(bot, cog_properties)

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


def add_inspire_cog(bot):
    bot.add_cog(InspireQuote(bot))


def add_wotd_cog(bot, cog_properties):
    post_channel_id = check_and_get_property(cog_properties, "wotd", "postChannelId")
    bot.add_cog(WordOfTheDay(bot, post_channel_id))


def add_stocks_cog(bot, cog_properties):
    post_channel_id = check_and_get_property(cog_properties, "stocks", "postChannelId")
    polygon_api_key = check_and_get_property(cog_properties, "stocks", "polygonAPIKey")
    stock_list = check_and_get_property(cog_properties, "stocks", "stockList")
    bot.add_cog(StockQuote(bot, stock_list, polygon_api_key, post_channel_id))


def add_twitch_cog(bot, cog_properties):
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
            twitch_client_id,
            twitch_client_secret,
            post_channel_id,
            join_channel_list,
        )
    )


def add_reddit_cog(bot, cog_properties):
    post_channel_id = check_and_get_property(cog_properties, "reddit", "postChannelId")
    reddit_client = check_and_get_property(cog_properties, "reddit", "redditClient")
    reddit_secret = check_and_get_property(cog_properties, "reddit", "redditSecret")
    reddit_username = check_and_get_property(cog_properties, "reddit", "redditUsername")
    reddit_password = check_and_get_property(cog_properties, "reddit", "redditPassword")
    subreddit_list = check_and_get_property(cog_properties, "reddit", "subRedditList")
    bot.add_cog(
        Reddit(
            bot,
            reddit_client,
            reddit_secret,
            reddit_username,
            reddit_password,
            subreddit_list,
            post_channel_id,
        )
    )


def add_ai_cog(bot, cog_properties):
    ollama_endpoint = check_and_get_property(cog_properties, "ai", "ollamaEndpoint")
    ollama_llm_model = check_and_get_property(cog_properties, "ai", "ollamaLLMModel")
    google_api_key = check_and_get_property(cog_properties, "ai", "googleAPIKey")
    google_llm_model = check_and_get_property(cog_properties, "ai", "googleLLMModel")
    groq_api_key = check_and_get_property(cog_properties, "ai", "groqAPIKey")
    groq_llm_model = check_and_get_property(cog_properties, "ai", "groqLLMModel")
    ai_system_prompt = check_and_get_property(cog_properties, "ai", "systemPrompt")
    bot.add_cog(
        AI(
            bot,
            ollama_endpoint,
            ollama_llm_model,
            google_api_key,
            google_llm_model,
            groq_api_key,
            groq_llm_model,
            ai_system_prompt,
        )
    )
