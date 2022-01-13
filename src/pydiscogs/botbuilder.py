from discord.ext import commands
from pyaml_env import parse_config
config = parse_config('./tests/testbot.yaml')

print(config)