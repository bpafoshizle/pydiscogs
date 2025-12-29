import logging
import os
import re
from enum import Enum
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field
from xdk import Client

logger = logging.getLogger(__name__)


class TweetField(str, Enum):
    """Available tweet fields from X API v2."""

    ARTICLE = "article"
    ATTACHMENTS = "attachments"
    AUTHOR_ID = "author_id"
    CARD_URI = "card_uri"
    COMMUNITY_ID = "community_id"
    CONTEXT_ANNOTATIONS = "context_annotations"
    CONVERSATION_ID = "conversation_id"
    CREATED_AT = "created_at"
    DISPLAY_TEXT_RANGE = "display_text_range"
    EDIT_CONTROLS = "edit_controls"
    EDIT_HISTORY_TWEET_IDS = "edit_history_tweet_ids"
    ENTITIES = "entities"
    GEO = "geo"
    ID = "id"
    IN_REPLY_TO_USER_ID = "in_reply_to_user_id"
    LANG = "lang"
    MEDIA_METADATA = "media_metadata"
    NON_PUBLIC_METRICS = "non_public_metrics"
    NOTE_TWEET = "note_tweet"
    ORGANIC_METRICS = "organic_metrics"
    POSSIBLY_SENSITIVE = "possibly_sensitive"
    PROMOTED_METRICS = "promoted_metrics"
    PUBLIC_METRICS = "public_metrics"
    REFERENCED_TWEETS = "referenced_tweets"
    REPLY_SETTINGS = "reply_settings"
    SCOPES = "scopes"
    SOURCE = "source"
    SUGGESTED_SOURCE_LINKS = "suggested_source_links"
    TEXT = "text"
    WITHHELD = "withheld"


class Expansion(str, Enum):
    """Available expansions from X API v2."""

    ARTICLE_COVER_MEDIA = "article.cover_media"
    ARTICLE_MEDIA_ENTITIES = "article.media_entities"
    ATTACHMENTS_MEDIA_KEYS = "attachments.media_keys"
    ATTACHMENTS_MEDIA_SOURCE_TWEET = "attachments.media_source_tweet"
    ATTACHMENTS_POLL_IDS = "attachments.poll_ids"
    AUTHOR_ID = "author_id"
    EDIT_HISTORY_TWEET_IDS = "edit_history_tweet_ids"
    ENTITIES_MENTIONS_USERNAME = "entities.mentions.username"
    GEO_PLACE_ID = "geo.place_id"
    IN_REPLY_TO_USER_ID = "in_reply_to_user_id"
    ENTITIES_NOTE_MENTIONS_USERNAME = "entities.note.mentions.username"
    REFERENCED_TWEETS_ID = "referenced_tweets.id"
    REFERENCED_TWEETS_ID_ATTACHMENTS_MEDIA_KEYS = (
        "referenced_tweets.id.attachments.media_keys"
    )
    REFERENCED_TWEETS_ID_AUTHOR_ID = "referenced_tweets.id.author_id"


class MediaField(str, Enum):
    """Available media fields from X API v2."""

    ALT_TEXT = "alt_text"
    DURATION_MS = "duration_ms"
    HEIGHT = "height"
    MEDIA_KEY = "media_key"
    NON_PUBLIC_METRICS = "non_public_metrics"
    ORGANIC_METRICS = "organic_metrics"
    PREVIEW_IMAGE_URL = "preview_image_url"
    PROMOTED_METRICS = "promoted_metrics"
    PUBLIC_METRICS = "public_metrics"
    TYPE = "type"
    URL = "url"
    VARIANTS = "variants"
    WIDTH = "width"


class PollField(str, Enum):
    """Available poll fields from X API v2."""

    DURATION_MINUTES = "duration_minutes"
    END_DATETIME = "end_datetime"
    ID = "id"
    OPTIONS = "options"
    VOTING_STATUS = "voting_status"


class UserField(str, Enum):
    """Available user fields from X API v2."""

    AFFILIATION = "affiliation"
    CONFIRMED_EMAIL = "confirmed_email"
    CONNECTION_STATUS = "connection_status"
    CREATED_AT = "created_at"
    DESCRIPTION = "description"
    ENTITIES = "entities"
    ID = "id"
    IS_IDENTITY_VERIFIED = "is_identity_verified"
    LOCATION = "location"
    MOST_RECENT_TWEET_ID = "most_recent_tweet_id"
    NAME = "name"
    PARODY = "parody"
    PINNED_TWEET_ID = "pinned_tweet_id"
    PROFILE_BANNER_URL = "profile_banner_url"
    PROFILE_IMAGE_URL = "profile_image_url"
    PROTECTED = "protected"
    PUBLIC_METRICS = "public_metrics"
    RECEIVES_YOUR_DM = "receives_your_dm"
    SUBSCRIPTION = "subscription"
    SUBSCRIPTION_TYPE = "subscription_type"
    URL = "url"
    USERNAME = "username"
    VERIFIED = "verified"
    VERIFIED_FOLLOWERS_COUNT = "verified_followers_count"
    VERIFIED_TYPE = "verified_type"
    WITHHELD = "withheld"


class PlaceField(str, Enum):
    """Available place fields from X API v2."""

    CONTAINED_WITHIN = "contained_within"
    COUNTRY = "country"
    COUNTRY_CODE = "country_code"
    FULL_NAME = "full_name"
    GEO = "geo"
    ID = "id"
    NAME = "name"
    PLACE_TYPE = "place_type"


# Default configurations for rich data retrieval
DEFAULT_TWEET_FIELDS = [
    TweetField.ARTICLE,
    TweetField.ATTACHMENTS,
    TweetField.AUTHOR_ID,
    TweetField.CONTEXT_ANNOTATIONS,
    TweetField.CONVERSATION_ID,
    TweetField.CREATED_AT,
    TweetField.ENTITIES,
    TweetField.GEO,
    TweetField.ID,
    TweetField.IN_REPLY_TO_USER_ID,
    TweetField.LANG,
    TweetField.PUBLIC_METRICS,
    TweetField.POSSIBLY_SENSITIVE,
    TweetField.REFERENCED_TWEETS,
    TweetField.REPLY_SETTINGS,
    TweetField.SOURCE,
    TweetField.TEXT,
]

DEFAULT_EXPANSIONS = [
    Expansion.AUTHOR_ID,
    Expansion.ATTACHMENTS_MEDIA_KEYS,
    Expansion.ATTACHMENTS_POLL_IDS,
    Expansion.GEO_PLACE_ID,
    Expansion.IN_REPLY_TO_USER_ID,
    Expansion.REFERENCED_TWEETS_ID,
    Expansion.REFERENCED_TWEETS_ID_AUTHOR_ID,
    Expansion.ENTITIES_MENTIONS_USERNAME,
]

DEFAULT_MEDIA_FIELDS = [
    MediaField.ALT_TEXT,
    MediaField.DURATION_MS,
    MediaField.HEIGHT,
    MediaField.MEDIA_KEY,
    MediaField.PREVIEW_IMAGE_URL,
    MediaField.PUBLIC_METRICS,
    MediaField.TYPE,
    MediaField.URL,
    MediaField.VARIANTS,
    MediaField.WIDTH,
]

DEFAULT_POLL_FIELDS = [
    PollField.DURATION_MINUTES,
    PollField.END_DATETIME,
    PollField.ID,
    PollField.OPTIONS,
    PollField.VOTING_STATUS,
]

DEFAULT_USER_FIELDS = [
    UserField.CREATED_AT,
    UserField.DESCRIPTION,
    UserField.ENTITIES,
    UserField.ID,
    UserField.LOCATION,
    UserField.NAME,
    UserField.PROFILE_IMAGE_URL,
    UserField.PROTECTED,
    UserField.PUBLIC_METRICS,
    UserField.URL,
    UserField.USERNAME,
    UserField.VERIFIED,
    UserField.VERIFIED_TYPE,
]

DEFAULT_PLACE_FIELDS = [
    PlaceField.CONTAINED_WITHIN,
    PlaceField.COUNTRY,
    PlaceField.COUNTRY_CODE,
    PlaceField.FULL_NAME,
    PlaceField.GEO,
    PlaceField.ID,
    PlaceField.NAME,
    PlaceField.PLACE_TYPE,
]


class ReadXPostInput(BaseModel):
    url_or_id: str = Field(description="The URL or ID of the X (Twitter) post to read.")


class ReadXPostTool(BaseTool):
    """A tool for reading an X (Twitter) post given a URL or post ID. Links to posts on X (formerly twitter)
    cannot be read by normal web or url reading tools."""

    name: str = "read_x_post"
    description: str = "Reads the content of an X (Twitter) post given its URL or ID."
    args_schema: Type[BaseModel] = ReadXPostInput

    # Configurable fields and expansions
    tweet_fields: list[TweetField] = DEFAULT_TWEET_FIELDS
    expansions: list[Expansion] = DEFAULT_EXPANSIONS
    media_fields: list[MediaField] = DEFAULT_MEDIA_FIELDS
    poll_fields: list[PollField] = DEFAULT_POLL_FIELDS
    user_fields: list[UserField] = DEFAULT_USER_FIELDS
    place_fields: list[PlaceField] = DEFAULT_PLACE_FIELDS

    def _run(self, url_or_id: str) -> str:
        """Use the tool."""
        post_id = self._extract_post_id(url_or_id)
        if not post_id:
            return "Error: Could not extract a valid post ID from the input."

        logger.info("'Lay off me, daddy.' - Sean Michaels")

        try:
            client = Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
            )

            # Build parameters with configured fields (as lists, not comma-separated strings)
            params = {
                "ids": [post_id],
                "tweet_fields": [field.value for field in self.tweet_fields],
                "expansions": [exp.value for exp in self.expansions],
                "media_fields": [field.value for field in self.media_fields],
                "poll_fields": [field.value for field in self.poll_fields],
                "user_fields": [field.value for field in self.user_fields],
                "place_fields": [field.value for field in self.place_fields],
            }

            response = client.posts.get_by_ids(**params)

            if not response or not response.data:
                return f"Error: No post found with ID {post_id}."

            logger.debug(f"Full X Post Data: {response.data}")

            # Format comprehensive response
            post = response.data[0]
            result = self._format_post_data(post, response)

            return result

        except Exception as e:
            logger.error(f"Error reading X post: {e}", exc_info=True)
            return f"Error reading X post: {str(e)}"

    def _format_post_data(self, post: dict, response) -> str:
        """Format the post data into a readable string with all available information."""
        lines = ["=== X Post ===\n"]

        # Basic info
        lines.append(f"Text: {post.get('text', 'N/A')}")
        lines.append(f"ID: {post.get('id', 'N/A')}")

        if "created_at" in post:
            lines.append(f"Created: {post['created_at']}")

        # Article content (expanded content from X articles)
        if "article" in post:
            article = post["article"]
            lines.append("\n=== Article Content ===")

            if "title" in article:
                lines.append(f"\nTitle: {article['title']}")

            # if 'preview_text' in article:
            #     lines.append(f"\nPreview: {article['preview_text']}")

            if "plain_text" in article:
                lines.append("\n--- Full Article Text ---")
                lines.append(article["plain_text"])
                lines.append("--- End Article Text ---")

            if "cover_media" in article:
                lines.append(f"\nCover Media ID: {article['cover_media']}")

            if "media_entities" in article and article["media_entities"]:
                lines.append(f"Article Media: {', '.join(article['media_entities'])}")

        # Metrics
        if "public_metrics" in post:
            metrics = post["public_metrics"]
            lines.append("\nEngagement Metrics:")
            lines.append(f"  - Retweets: {metrics.get('retweet_count', 0)}")
            lines.append(f"  - Replies: {metrics.get('reply_count', 0)}")
            lines.append(f"  - Likes: {metrics.get('like_count', 0)}")
            lines.append(f"  - Quotes: {metrics.get('quote_count', 0)}")
            lines.append(f"  - Bookmarks: {metrics.get('bookmark_count', 0)}")
            lines.append(f"  - Impressions: {metrics.get('impression_count', 0)}")

        # Author info (from includes)
        if hasattr(response, "includes") and response.includes:
            includes = response.includes

            if hasattr(includes, "users") and includes.users:
                user = includes.users[0]
                lines.append(
                    f"\nAuthor: @{user.get('username', 'N/A')} ({user.get('name', 'N/A')})"
                )
                if "description" in user:
                    lines.append(f"Bio: {user['description']}")
                if "public_metrics" in user:
                    um = user["public_metrics"]
                    lines.append(
                        f"Followers: {um.get('followers_count', 0)} | Following: {um.get('following_count', 0)}"
                    )

            # Media info
            if hasattr(includes, "media") and includes.media:
                lines.append(f"\nMedia: {len(includes.media)} item(s)")
                for i, media in enumerate(includes.media, 1):
                    media_type = media.get("type", "unknown")
                    lines.append(f"  {i}. Type: {media_type}")
                    if "url" in media:
                        lines.append(f"     URL: {media['url']}")
                    if "alt_text" in media:
                        lines.append(f"     Alt: {media['alt_text']}")

            # Poll info
            if hasattr(includes, "polls") and includes.polls:
                poll = includes.polls[0]
                lines.append(f"\nPoll: {poll.get('voting_status', 'unknown')}")
                if "options" in poll:
                    for opt in poll["options"]:
                        lines.append(
                            f"  - {opt.get('label', 'N/A')}: {opt.get('votes', 0)} votes"
                        )

            # Place info
            if hasattr(includes, "places") and includes.places:
                place = includes.places[0]
                lines.append(f"\nLocation: {place.get('full_name', 'N/A')}")

        # Entities (URLs, mentions, hashtags)
        if "entities" in post:
            entities = post["entities"]
            if "urls" in entities and entities["urls"]:
                lines.append(f"\nURLs: {len(entities['urls'])} link(s)")
                for url in entities["urls"]:
                    lines.append(
                        f"  - {url.get('expanded_url', url.get('url', 'N/A'))}"
                    )

            if "mentions" in entities and entities["mentions"]:
                mentions = [f"@{m['username']}" for m in entities["mentions"]]
                lines.append(f"\nMentions: {', '.join(mentions)}")

            if "hashtags" in entities and entities["hashtags"]:
                hashtags = [f"#{h['tag']}" for h in entities["hashtags"]]
                lines.append(f"\nHashtags: {', '.join(hashtags)}")

        # Referenced tweets (replies, quotes, retweets)
        if "referenced_tweets" in post:
            lines.append("\nReferenced Tweets:")
            for ref in post["referenced_tweets"]:
                lines.append(
                    f"  - {ref.get('type', 'unknown')}: {ref.get('id', 'N/A')}"
                )

        # Additional metadata
        if "lang" in post:
            lines.append(f"\nLanguage: {post['lang']}")

        if "source" in post:
            lines.append(f"Source: {post['source']}")

        if "conversation_id" in post:
            lines.append(f"Conversation ID: {post['conversation_id']}")

        return "\n".join(lines)

    def _extract_post_id(self, url_or_id: str) -> Optional[str]:
        # Check if it's already just digits
        if re.match(r"^\d+$", url_or_id):
            return url_or_id

        # Try to extract from URL
        # Matches patterns like:
        # https://x.com/username/status/1234567890
        # https://twitter.com/username/status/1234567890
        match = re.search(r"status/(\d+)", url_or_id)
        if match:
            return match.group(1)

        return None
