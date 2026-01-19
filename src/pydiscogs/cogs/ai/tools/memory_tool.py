from typing import Literal, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class UpsertMemoryInput(BaseModel):
    key: str = Field(
        ...,
        description="The key to store the memory under (e.g., 'favorite_language').",
    )
    value: str = Field(..., description="The information to store (e.g., 'Python').")
    scope: Literal["user", "guild", "channel"] = Field(
        "user",
        description="The scope of the memory. 'user' for private user facts, 'guild' for server-wide facts, 'channel' for channel-specific context.",
    )


class UpsertMemoryTool(BaseTool):
    name: str = "upsert_memory"
    description: str = (
        "Saves a piece of information into long-term memory. "
        "Use this to remember preferences, facts, or context that should "
        "persist across different conversations. Choose the appropriate scope."
    )
    args_schema: Type[BaseModel] = UpsertMemoryInput
    store: object = None
    user_id: str = None
    guild_id: str = None
    channel_id: str = None

    def __init__(
        self, store, user_id: str, guild_id: str = None, channel_id: str = None
    ):
        super().__init__()
        self.store = store
        self.user_id = user_id
        self.guild_id = guild_id
        self.channel_id = channel_id

    def _run(self, key: str, value: str, scope: str = "user") -> str:
        """Synchronous version - not implemented/used."""
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, key: str, value: str, scope: str = "user") -> str:
        if not self.store:
            return "Error: Memory store not configured."

        namespace = None
        if scope == "user":
            if not self.user_id:
                return "Error: User ID not available for user scope."
            namespace = (self.user_id, "memories")
        elif scope == "guild":
            if not self.guild_id:
                return "Error: Guild ID not available for guild scope."
            namespace = (self.guild_id, "memories")
        elif scope == "channel":
            if not self.channel_id:
                return "Error: Channel ID not available for channel scope."
            namespace = (self.channel_id, "memories")
        else:
            return f"Error: Invalid scope '{scope}'."

        # Determine strictness for scope
        # User memories are naturally private due to user_id namespace
        # Guild/Channel memories are shared with anyone in that guild/channel

        await self.store.aput(namespace, key, {"data": value})
        return f"Stored memory ({scope}): {key} = {value}"
