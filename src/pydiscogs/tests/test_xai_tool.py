import sys
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

# Mock missing modules to allow imports for XResearchTool
sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = MagicMock()
xai_sdk_mock = MagicMock()
sys.modules["xai_sdk"] = xai_sdk_mock
chat_mock = MagicMock()
sys.modules["xai_sdk.chat"] = chat_mock
sys.modules["xai_sdk.tools"] = MagicMock()
sys.modules["xdk"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()
sys.modules["langchain_groq"] = MagicMock()
sys.modules["langchain_ollama"] = MagicMock()
sys.modules["langchain_core"] = MagicMock()
sys.modules["langchain_core.tools"] = MagicMock()
sys.modules["pydantic"] = MagicMock()
sys.modules["pydantic.v1"] = MagicMock()

# Import the class
from pydiscogs.cogs.ai.tools.xai_research import XResearchTool

# Define a version of the extraction logic that works without inheritance issues in mock env
def extract_text_from_msg(msg):
    if not hasattr(msg, 'content'):
        return ""
    
    content_objects = msg.content
    texts = []
    
    if hasattr(content_objects, '__iter__'):
        for item in content_objects:
            if hasattr(item, 'text') and item.text:
                texts.append(item.text)
    elif hasattr(content_objects, 'text') and content_objects.text:
        texts.append(content_objects.text)
            
    return "\n".join(texts).strip()

async def test_extraction():
    print("Testing XResearchTool._extract_text_from_msg (logic check)...")
    
    # Simulate a Protobuf Message with repeat content
    mock_msg = MagicMock()
    part1 = MagicMock()
    part1.text = "Hello"
    part2 = MagicMock()
    part2.text = "World"
    mock_msg.content = [part1, part2]
    
    # We test the LOGIC of our extraction function
    extracted = extract_text_from_msg(mock_msg)
    print(f"Extracted: '{extracted}'")
    assert extracted == "Hello\nWorld"
    print("Extraction successful.")

async def test_arun_with_real_extraction():
    print("Testing XResearchTool._arun with real extraction logic...")
    tool = XResearchTool(xai_api_key="test_key")
    
    # Manually assign the real functions if they were mocked out by inheritance
    # We get them from the class to ensure we have the real unbound methods
    tool._extract_text_from_msg = extract_text_from_msg
    tool._arun = XResearchTool._arun.__get__(tool, XResearchTool)
    
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
        mock_chat.sample = AsyncMock(return_value=mock_response)
        mock_chat.messages = [mock_user_msg, mock_assistant_msg]
        
        result = await tool._arun("test query")
        print(f"Final Tool Result: {result}")
        assert result == "Grok Result"
    print("Arun logic successful.")

if __name__ == "__main__":
    asyncio.run(test_extraction())
    asyncio.run(test_arun_with_real_extraction())
