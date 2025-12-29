"""test_ai_tools.py
Testing AI tools: web_research, url_context, and read_x_post
"""

import os
import unittest
from unittest.mock import MagicMock, patch

import sys
from unittest.mock import MagicMock

# Mock missing modules to allow imports for tools
# We use dummy classes for BaseTool/BaseModel to allow inheritance to work
class MockBaseTool:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockBaseModel:
    pass

def MockField(**kwargs):
    return MagicMock()

mock_langchain_core_tools = MagicMock()
mock_langchain_core_tools.BaseTool = MockBaseTool
sys.modules["langchain_core.tools"] = mock_langchain_core_tools

mock_pydantic_v1 = MagicMock()
mock_pydantic_v1.BaseModel = MockBaseModel
mock_pydantic_v1.Field = MockField
sys.modules["pydantic.v1"] = mock_pydantic_v1
sys.modules["pydantic"] = MagicMock()  # generic pydantic

sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = MagicMock()
sys.modules["xai_sdk"] = MagicMock()
sys.modules["xai_sdk.chat"] = MagicMock()
sys.modules["xai_sdk.tools"] = MagicMock()
sys.modules["xdk"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()
sys.modules["langchain_groq"] = MagicMock()
sys.modules["langchain_ollama"] = MagicMock()
sys.modules["langchain_core"] = MagicMock()
# sys.modules["langchain_core.tools"] is already set above

# We don't mock pydantic/BaseModel fully because the tools use them for args_schema
# But if it causes issues we might need to, but usually pydantic is installed or we can mock it carefully.
# Assuming pydantic IS installed since the user code uses it heavily. 
# If not, we'd have trouble. But let's assume standard stuff like pydantic might be there 
# or if it fails we mock it too. The error was about 'google'.

from pydiscogs.cogs.ai.tools.read_x_post import (
    Expansion,
    ReadXPostInput,
    ReadXPostTool,
    TweetField,
)
from pydiscogs.cogs.ai.tools.url_context import UrlContextInput, UrlContextTool
from pydiscogs.cogs.ai.tools.web_research import WebResearchTool, WebSearchInput
from pydiscogs.cogs.ai.tools.xai_research import XResearchTool
from unittest.mock import AsyncMock


class TestWebResearchTool(unittest.TestCase):
    """Test cases for WebResearchTool"""

    def test_initialization(self):
        """Test that WebResearchTool initializes correctly with required parameters"""
        tool = WebResearchTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )
        self.assertEqual(tool.name, "web_research")
        self.assertEqual(tool.args_schema, WebSearchInput)
        self.assertIn("web research", tool.description.lower())
        self.assertEqual(tool.google_api_key, "test_api_key")
        self.assertEqual(tool.google_llm_model, "test_model")

    @patch("pydiscogs.cogs.ai.tools.web_research.Client")
    @patch("pydiscogs.cogs.ai.tools.web_research.get_current_date")
    def test_run_with_valid_query(self, mock_get_current_date, MockClient):
        """Test _run method with valid query and mocked Google client"""
        # Setup mocks
        mock_get_current_date.return_value = "2024-01-01"
        mock_response = MagicMock()
        mock_response.text = "Research results about test query"
        MockClient.return_value.models.generate_content.return_value = mock_response

        # Create tool and run
        tool = WebResearchTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )
        result = tool._run(query="test query")

        # Verify
        self.assertEqual(result, "Research results about test query")
        MockClient.assert_called_once_with(api_key="test_api_key")
        MockClient.return_value.models.generate_content.assert_called_once()

        # Verify the call arguments
        call_args = MockClient.return_value.models.generate_content.call_args
        self.assertEqual(call_args[1]["model"], "test_model")
        self.assertIn("test query", call_args[1]["contents"])
        self.assertEqual(call_args[1]["config"]["tools"], [{"google_search": {}}])
        self.assertEqual(call_args[1]["config"]["temperature"], 0)

    @patch("pydiscogs.cogs.ai.tools.web_research.Client")
    @patch("pydiscogs.cogs.ai.tools.web_research.get_current_date")
    def test_run_returns_response_text(self, mock_get_current_date, MockClient):
        """Test that _run returns the text property from the response"""
        mock_get_current_date.return_value = "2024-01-01"
        mock_response = MagicMock()
        mock_response.text = "Expected response text"
        MockClient.return_value.models.generate_content.return_value = mock_response

        tool = WebResearchTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )
        result = tool._run(query="query")

        self.assertEqual(result, "Expected response text")

    @patch("pydiscogs.cogs.ai.tools.web_research.Client")
    @patch("pydiscogs.cogs.ai.tools.web_research.get_current_date")
    def test_run_with_api_error(self, mock_get_current_date, MockClient):
        """Test error handling when Google client raises an exception"""
        mock_get_current_date.return_value = "2024-01-01"
        MockClient.return_value.models.generate_content.side_effect = Exception(
            "API Error"
        )

        tool = WebResearchTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )

        # Should raise the exception
        with self.assertRaises(Exception) as context:
            tool._run(query="test query")
        self.assertIn("API Error", str(context.exception))


class TestUrlContextTool(unittest.TestCase):
    """Test cases for UrlContextTool"""

    def test_initialization(self):
        """Test that UrlContextTool initializes correctly with required parameters"""
        tool = UrlContextTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )
        self.assertEqual(tool.name, "url_context")
        self.assertEqual(tool.args_schema, UrlContextInput)
        self.assertIn("research", tool.description.lower())
        self.assertEqual(tool.google_api_key, "test_api_key")
        self.assertEqual(tool.google_llm_model, "test_model")

    @patch("pydiscogs.cogs.ai.tools.url_context.Client")
    @patch("pydiscogs.cogs.ai.tools.url_context.get_current_date")
    def test_run_with_single_url(self, mock_get_current_date, MockClient):
        """Test _run with a single URL"""
        mock_get_current_date.return_value = "2024-01-01"
        mock_response = MagicMock()
        mock_response.text = "Context from single URL"
        MockClient.return_value.models.generate_content.return_value = mock_response

        tool = UrlContextTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )
        result = tool._run(urls=["https://example.com"], query="test query")

        self.assertEqual(result, "Context from single URL")
        call_args = MockClient.return_value.models.generate_content.call_args
        self.assertIn("https://example.com", call_args[1]["contents"])

    @patch("pydiscogs.cogs.ai.tools.url_context.Client")
    @patch("pydiscogs.cogs.ai.tools.url_context.get_current_date")
    def test_run_with_multiple_urls(self, mock_get_current_date, MockClient):
        """Test _run with multiple URLs, verify they're joined correctly"""
        mock_get_current_date.return_value = "2024-01-01"
        mock_response = MagicMock()
        mock_response.text = "Context from multiple URLs"
        MockClient.return_value.models.generate_content.return_value = mock_response

        tool = UrlContextTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )
        urls = ["https://example1.com", "https://example2.com", "https://example3.com"]
        result = tool._run(urls=urls, query="test query")

        self.assertEqual(result, "Context from multiple URLs")
        call_args = MockClient.return_value.models.generate_content.call_args
        # All URLs should be in the prompt
        for url in urls:
            self.assertIn(url, call_args[1]["contents"])

    @patch("pydiscogs.cogs.ai.tools.url_context.Client")
    @patch("pydiscogs.cogs.ai.tools.url_context.get_current_date")
    def test_run_returns_response_text(self, mock_get_current_date, MockClient):
        """Test that _run returns the text property from the response"""
        mock_get_current_date.return_value = "2024-01-01"
        mock_response = MagicMock()
        mock_response.text = "Expected URL context response"
        MockClient.return_value.models.generate_content.return_value = mock_response

        tool = UrlContextTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )
        result = tool._run(urls=["https://example.com"], query="query")

        self.assertEqual(result, "Expected URL context response")

    @patch("pydiscogs.cogs.ai.tools.url_context.Client")
    @patch("pydiscogs.cogs.ai.tools.url_context.get_current_date")
    def test_run_with_api_error(self, mock_get_current_date, MockClient):
        """Test error handling when Google client raises an exception"""
        mock_get_current_date.return_value = "2024-01-01"
        MockClient.return_value.models.generate_content.side_effect = Exception(
            "URL Context API Error"
        )

        tool = UrlContextTool(
            google_api_key="test_api_key", google_llm_model="test_model"
        )

        # Should raise the exception
        with self.assertRaises(Exception) as context:
            tool._run(urls=["https://example.com"], query="test query")
        self.assertIn("URL Context API Error", str(context.exception))


class TestReadXPostTool(unittest.TestCase):
    """Test cases for ReadXPostTool"""

    def test_initialization(self):
        """Test that ReadXPostTool initializes correctly with default configurations"""
        tool = ReadXPostTool()
        self.assertEqual(tool.name, "read_x_post")
        self.assertEqual(tool.args_schema, ReadXPostInput)
        self.assertIn("x", tool.description.lower())
        # Check default field configurations exist
        self.assertIsNotNone(tool.tweet_fields)
        self.assertIsNotNone(tool.expansions)
        self.assertIsNotNone(tool.media_fields)
        self.assertIsNotNone(tool.poll_fields)
        self.assertIsNotNone(tool.user_fields)
        self.assertIsNotNone(tool.place_fields)
        # Check some defaults are present
        self.assertIn(TweetField.ARTICLE, tool.tweet_fields)
        self.assertIn(Expansion.AUTHOR_ID, tool.expansions)

    def test_extract_post_id_from_numeric_id(self):
        """Test _extract_post_id with a numeric post ID"""
        tool = ReadXPostTool()
        result = tool._extract_post_id("1234567890")
        self.assertEqual(result, "1234567890")

    def test_extract_post_id_from_x_url(self):
        """Test _extract_post_id with x.com URL"""
        tool = ReadXPostTool()
        result = tool._extract_post_id("https://x.com/username/status/1234567890")
        self.assertEqual(result, "1234567890")

    def test_extract_post_id_from_twitter_url(self):
        """Test _extract_post_id with twitter.com URL"""
        tool = ReadXPostTool()
        result = tool._extract_post_id("https://twitter.com/username/status/9876543210")
        self.assertEqual(result, "9876543210")

    def test_extract_post_id_with_url_parameters(self):
        """Test _extract_post_id with URL that has query parameters"""
        tool = ReadXPostTool()
        result = tool._extract_post_id(
            "https://x.com/user/status/1234567890?s=20&t=abc123"
        )
        self.assertEqual(result, "1234567890")

    def test_extract_post_id_invalid_input(self):
        """Test _extract_post_id with invalid input returns None"""
        tool = ReadXPostTool()
        self.assertIsNone(tool._extract_post_id("not a valid id or url"))
        self.assertIsNone(tool._extract_post_id("https://example.com"))
        self.assertIsNone(tool._extract_post_id(""))

    @patch.dict(os.environ, {"X_BEARER_TOKEN": "test_bearer_token"})
    @patch("pydiscogs.cogs.ai.tools.read_x_post.Client")
    def test_run_with_valid_post_id(self, MockClient):
        """Test _run with valid post ID and mocked X client"""
        # Setup mock response
        mock_response = MagicMock()
        mock_post = {
            "id": "1234567890",
            "text": "Test tweet text",
            "created_at": "2024-01-01T12:00:00Z",
        }
        mock_response.data = [mock_post]
        
        # Add comprehensive includes to verify _format_post_data integration
        mock_response.includes = MagicMock()
        mock_response.includes.users = [{
            "username": "testuser",
            "name": "Test User",
            "description": "Bio",
            "public_metrics": {"followers_count": 100, "following_count": 10}
        }]
        mock_response.includes.media = [{
            "type": "photo",
            "url": "http://img.com",
            "alt_text": "Alt"
        }]
        mock_response.includes.polls = None
        mock_response.includes.places = None

        MockClient.return_value.posts.get_by_ids.return_value = mock_response

        tool = ReadXPostTool()
        result = tool._run(url_or_id="1234567890")

        # Verify result contains expected content from main post AND includes
        self.assertIn("Test tweet text", result)
        self.assertIn("1234567890", result)
        self.assertIn("X Post", result)
        # Check that includes were processed
        self.assertIn("@testuser", result)
        self.assertIn("Test User", result)
        self.assertIn("Bio", result)
        self.assertIn("Media: 1 item(s)", result)
        self.assertIn("http://img.com", result)

        # Verify client was called correctly
        MockClient.assert_called_once_with(bearer_token="test_bearer_token")
        call_kwargs = MockClient.return_value.posts.get_by_ids.call_args[1]
        self.assertEqual(call_kwargs["ids"], ["1234567890"])
        self.assertIn("tweet_fields", call_kwargs)
        self.assertIn("expansions", call_kwargs)

    def test_run_with_invalid_post_id(self):
        """Test _run with invalid post ID returns error message"""
        tool = ReadXPostTool()
        result = tool._run(url_or_id="invalid input")
        self.assertIn("Error", result)
        self.assertIn("valid post ID", result)

    @patch.dict(os.environ, {"X_BEARER_TOKEN": "test_bearer_token"})
    @patch("pydiscogs.cogs.ai.tools.read_x_post.Client")
    def test_run_with_no_post_found(self, MockClient):
        """Test _run when no post is found"""
        mock_response = MagicMock()
        mock_response.data = None
        MockClient.return_value.posts.get_by_ids.return_value = mock_response

        tool = ReadXPostTool()
        result = tool._run(url_or_id="1234567890")

        self.assertIn("Error", result)
        self.assertIn("No post found", result)

    @patch.dict(os.environ, {"X_BEARER_TOKEN": "test_bearer_token"})
    @patch("pydiscogs.cogs.ai.tools.read_x_post.Client")
    def test_run_with_api_error(self, MockClient):
        """Test error handling when X client raises an exception"""
        MockClient.return_value.posts.get_by_ids.side_effect = Exception("X API Error")

        tool = ReadXPostTool()
        result = tool._run(url_or_id="1234567890")

        self.assertIn("Error reading X post", result)
        self.assertIn("X API Error", result)

    def test_format_post_data_basic(self):
        """Test _format_post_data with basic post data (text, ID, created_at)"""
        tool = ReadXPostTool()
        post = {
            "id": "1234567890",
            "text": "This is a test tweet",
            "created_at": "2024-01-01T12:00:00Z",
        }
        mock_response = MagicMock()
        mock_response.includes = None

        result = tool._format_post_data(post, mock_response)

        self.assertIn("X Post", result)
        self.assertIn("This is a test tweet", result)
        self.assertIn("1234567890", result)
        self.assertIn("2024-01-01T12:00:00Z", result)

    def test_format_post_data_with_article(self):
        """Test _format_post_data includes article content (title, plain_text)"""
        tool = ReadXPostTool()
        post = {
            "id": "1234567890",
            "text": "Check out this article",
            "article": {
                "title": "Test Article Title",
                "preview_text": "This is a preview",
                "plain_text": "This is the full article text with more details.",
            },
        }
        mock_response = MagicMock()
        mock_response.includes = None

        result = tool._format_post_data(post, mock_response)

        self.assertIn("Article Content", result)
        self.assertIn("Test Article Title", result)
        # self.assertIn("This is a preview", result)  # Removed as preview_text is commented out in code
        self.assertIn("This is the full article text with more details.", result)

    def test_format_post_data_with_metrics(self):
        """Test _format_post_data includes public_metrics"""
        tool = ReadXPostTool()
        post = {
            "id": "1234567890",
            "text": "Popular tweet",
            "public_metrics": {
                "retweet_count": 100,
                "reply_count": 50,
                "like_count": 500,
                "quote_count": 25,
                "bookmark_count": 75,
                "impression_count": 10000,
            },
        }
        mock_response = MagicMock()
        mock_response.includes = None

        result = tool._format_post_data(post, mock_response)

        self.assertIn("Engagement Metrics", result)
        self.assertIn("Retweets: 100", result)
        self.assertIn("Replies: 50", result)
        self.assertIn("Likes: 500", result)
        self.assertIn("Quotes: 25", result)
        self.assertIn("Bookmarks: 75", result)
        self.assertIn("Impressions: 10000", result)

    def test_format_post_data_with_media(self):
        """Test _format_post_data includes media information"""
        tool = ReadXPostTool()
        post = {"id": "1234567890", "text": "Tweet with media"}
        mock_response = MagicMock()
        mock_response.includes = MagicMock()
        mock_response.includes.users = None
        mock_response.includes.polls = None
        mock_response.includes.places = None
        mock_response.includes.media = [
            {
                "type": "photo",
                "url": "https://example.com/photo.jpg",
                "alt_text": "Photo description",
            },
            {"type": "video", "url": "https://example.com/video.mp4"},
        ]

        result = tool._format_post_data(post, mock_response)

        self.assertIn("Media: 2 item(s)", result)
        self.assertIn("Type: photo", result)
        self.assertIn("https://example.com/photo.jpg", result)
        self.assertIn("Photo description", result)
        self.assertIn("Type: video", result)

    def test_format_post_data_with_polls(self):
        """Test _format_post_data includes poll information"""
        tool = ReadXPostTool()
        post = {"id": "1234567890", "text": "Tweet with poll"}
        mock_response = MagicMock()
        mock_response.includes = MagicMock()
        mock_response.includes.users = None
        mock_response.includes.media = None
        mock_response.includes.places = None
        mock_response.includes.polls = [
            {
                "voting_status": "closed",
                "options": [
                    {"label": "Option A", "votes": 100},
                    {"label": "Option B", "votes": 150},
                ],
            }
        ]

        result = tool._format_post_data(post, mock_response)

        self.assertIn("Poll: closed", result)
        self.assertIn("Option A: 100 votes", result)
        self.assertIn("Option B: 150 votes", result)

    def test_format_post_data_with_author(self):
        """Test _format_post_data includes author information"""
        tool = ReadXPostTool()
        post = {"id": "1234567890", "text": "Tweet with author info"}
        mock_response = MagicMock()
        mock_response.includes = MagicMock()
        mock_response.includes.media = None
        mock_response.includes.polls = None
        mock_response.includes.places = None
        mock_response.includes.users = [
            {
                "username": "testuser",
                "name": "Test User",
                "description": "Test bio description",
                "public_metrics": {"followers_count": 1000, "following_count": 500},
            }
        ]

        result = tool._format_post_data(post, mock_response)

        self.assertIn("@testuser", result)
        self.assertIn("Test User", result)
        self.assertIn("Test bio description", result)
        self.assertIn("Followers: 1000", result)
        self.assertIn("Following: 500", result)

    def test_format_post_data_with_entities(self):
        """Test _format_post_data includes URLs, mentions, hashtags"""
        tool = ReadXPostTool()
        post = {
            "id": "1234567890",
            "text": "Tweet with entities",
            "entities": {
                "urls": [
                    {"url": "https://t.co/abc", "expanded_url": "https://example.com"}
                ],
                "mentions": [{"username": "user1"}, {"username": "user2"}],
                "hashtags": [{"tag": "python"}, {"tag": "testing"}],
            },
        }
        mock_response = MagicMock()
        mock_response.includes = None

        result = tool._format_post_data(post, mock_response)

        self.assertIn("https://example.com", result)
        self.assertIn("@user1", result)
        self.assertIn("@user2", result)
        self.assertIn("#python", result)
        self.assertIn("#testing", result)

    def test_format_post_data_with_referenced_tweets(self):
        """Test _format_post_data includes referenced tweets (replies, quotes, retweets)"""
        tool = ReadXPostTool()
        post = {
            "id": "1234567890",
            "text": "This is a reply",
            "referenced_tweets": [{"type": "replied_to", "id": "9876543210"}],
        }
        mock_response = MagicMock()
        mock_response.includes = None

        result = tool._format_post_data(post, mock_response)

        self.assertIn("Referenced Tweets", result)
        self.assertIn("replied_to", result)
        self.assertIn("9876543210", result)

    def test_format_post_data_with_additional_metadata(self):
        """Test _format_post_data includes language, source, and conversation ID"""
        tool = ReadXPostTool()
        post = {
            "id": "1234567890",
            "text": "Tweet with metadata",
            "lang": "en",
            "source": "Twitter Web App",
            "conversation_id": "1234567890",
        }
        mock_response = MagicMock()
        mock_response.includes = None

        result = tool._format_post_data(post, mock_response)

        self.assertIn("Language: en", result)
        self.assertIn("Source: Twitter Web App", result)
        self.assertIn("Conversation ID: 1234567890", result)



class TestXResearchTool(unittest.IsolatedAsyncioTestCase):
    """Test cases for XResearchTool"""

    def test_extraction_logic(self):
        """Test _extract_text_from_msg logic"""
        # Simulate a Protobuf Message with repeat content
        mock_msg = MagicMock()
        part1 = MagicMock()
        part1.text = "Hello"
        part2 = MagicMock()
        part2.text = "World"
        mock_msg.content = [part1, part2]

        # Use the tool's method (instantiate with dummy key)
        tool = XResearchTool(xai_api_key="test_key")
        
        extracted = tool._extract_text_from_msg(mock_msg)
        self.assertEqual(extracted, "Hello\nWorld")

    async def test_arun_with_real_extraction(self):
        """Test _arun with mocked client but real extraction logic"""
        tool = XResearchTool(xai_api_key="test_key")

        with patch("pydiscogs.cogs.ai.tools.xai_research.AsyncClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_chat = MagicMock()
            mock_instance.chat.create.return_value = mock_chat

            # Mock assistant response returning text
            mock_assistant_msg = MagicMock()
            mock_assistant_msg.role = 2
            mock_part = MagicMock()
            mock_part.text = "Grok Result"
            mock_assistant_msg.content = [mock_part]

            # User message at index 0, Assistant at index 1
            mock_user_msg = MagicMock()
            mock_user_msg.role = 1

            mock_response = MagicMock()
            mock_response.message = mock_assistant_msg
            
            # Ensure content is None to force logic to scan history/message (fallback path)
            # OR ensuring that if it checks message.content it finds our mock_part
            # The tool logic checks `response.content`. If we mock response.content to be None
            # it might fall back to chat history.
            # IN THE ORIGINAL TEST `test_xai_tool.py`, it mocked `chat.sample` returning `mock_response`.
            # `mock_response.message` was set. `mock_response.content` was NOT set (automagically MagicMock would make it a Mock, which is truthy!)
            # So `if response.content:` would be true in the original test unless `response` was a real object or specific mock config.
            # But the original test `test_arun_with_real_extraction` asserted "Grok Result".
            # If `response.content` was a MagicMock, `str(response.content)` would be a mock string.
            # So the tool must have hit the fallback?
            # Let's set `mock_response.content = None` to be safe and deterministic, forcing fallback to extraction from history
            # which we know works because we populate `mock_chat.messages`.
            mock_response.content = None 

            mock_chat.sample = AsyncMock(return_value=mock_response)
            mock_chat.messages = [mock_user_msg, mock_assistant_msg]

            result = await tool._arun("test query")
            self.assertEqual(result, "Grok Result")


if __name__ == "__main__":
    unittest.main()
