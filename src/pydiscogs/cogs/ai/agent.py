import logging
from typing import Literal

from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph

from .tools.memory_tool import UpsertMemoryTool

logger = logging.getLogger(__name__)


def build_agent_graph(llm, tools, system_prompt: str, checkpointer=None, store=None):
    """
    Builds a LangGraph state graph with ReAct agent logic, conversation summarization,
    and cross-thread long-term memory.
    """

    # Define the State
    class State(MessagesState):
        summary: str

    # Define Nodes
    async def call_model(state: State, config: RunnableConfig):
        messages = state["messages"]

        # Cross-Thread Memory Retrieval
        # Cross-Thread Semantic Memory Retrieval
        if store:
            configurable = config.get("configurable", {})
            user_id = configurable.get("user_id")
            guild_id = configurable.get("guild_id")
            channel_id = configurable.get("channel_id")

            # Find last human message for query
            query = None
            for m in reversed(messages):
                if isinstance(m, HumanMessage):
                    if isinstance(m.content, list):
                        # Extract text from list content (multimodal structure)
                        text_parts = [
                            block["text"]
                            for block in m.content
                            if isinstance(block, dict) and block.get("type") == "text"
                        ]
                        query = " ".join(text_parts)
                    else:
                        query = m.content
                    break

            if user_id and query:
                memories = []
                # User Scope
                user_mems = await store.asearch(
                    (user_id, "memories"), query=query, limit=3
                )
                for m in user_mems:
                    memories.append(f"[User] {m.key}: {m.value.get('data')}")

                # Guild Scope
                if guild_id:
                    guild_mems = await store.asearch(
                        (guild_id, "memories"), query=query, limit=3
                    )
                    for m in guild_mems:
                        memories.append(f"[Guild] {m.key}: {m.value.get('data')}")

                # Channel Scope
                if channel_id:
                    channel_mems = await store.asearch(
                        (channel_id, "memories"), query=query, limit=3
                    )
                    for m in channel_mems:
                        memories.append(f"[Channel] {m.key}: {m.value.get('data')}")

                if memories:
                    memory_content = "\n".join(memories)
                    memory_system_msg = f"Relevant memories:\n{memory_content}"
                    messages = [SystemMessage(content=memory_system_msg)] + messages

        # If there is a summary, prepend it to the messages
        summary = state.get("summary", "")
        if summary:
            # Add summary as system message context
            system_message = f"Summary of conversation earlier: {summary}"
            messages = [SystemMessage(content=system_message)] + messages

        # Combine System Prompt and Memory Instruction into one cohesive message
        full_system_prompt = ""

        if system_prompt:
            full_system_prompt += f"{system_prompt}\n\n"

        full_system_prompt += (
            "### MEMORY CAPABILITIES ###\n"
            "You are equipped with a long-term memory. You have access to the 'upsert_memory' tool to persist information.\n"
            "WHEN TO USE IT:\n"
            "1. User explicitly asks you to remember something (e.g., 'Remember that the WiFi password is 1234').\n"
            "2. User provides a significant fact that should be known later (e.g., 'Our staging server IP is 10.0.0.50').\n"
            "3. You learn a user preference (e.g., 'I only code in Python').\n\n"
            "HOW TO USE IT:\n"
            "- For user-specific facts/preferences: scope='user', key='preference_name', value='preference_value'\n"
            "- For server/guild-wide facts (e.g. IPs, rules, schedules): scope='guild', key='fact_name', value='fact_value'\n"
            "- For channel-specific context: scope='channel', key='context_name', value='context_value'\n\n"
            "IMPORTANT: Do NOT say you cannot remember things. You CAN. Just use the tool."
        )

        # Inject the unified system message
        messages = [SystemMessage(content=full_system_prompt)] + messages

        # Bind tools including UpsertMemory if store is available
        bound_llm = llm

        # active_tools = list(tools)
        if store:
            # We need to create the tool instance with the user_id from config?
            # No, ToolNode needs static tools usually.
            # Actually, we can just bind the tool definition and let the ToolNode handle it
            # BUT UpsertMemoryTool needs 'store' and 'user_id' at runtime.
            # Trick: We initialize UpsertMemoryTool with just 'store', and 'user_id'
            # will be injected or passed?
            # Easier: Creating a fresh tool instance inside the node isn't quite right for 'bind_tools'.
            # Better approach: The tool takes 'user_id' as an argument? No, that's insecure.
            # Correct approach involves LangGraph 'injected' args or custom ToolNode.
            # FOR VISIBILITY TO LLM: We simply bind the Tool class/schema.
            # EXECUTION: The ToolNode needs to run it.

            # Let's simplify: We will instantiate UpsertMemoryTool for THIS RUN inside the node
            # Wait, 'call_model' invokes LLM, it doesn't run tools.
            # 'tools' node runs tools.
            # So we need to add UpsertMemoryTool to the list of tools passed to ToolNode?
            # But it depends on 'user_id' which varies per request.
            pass

        # For now, let's assume we handle 'UpsertMemory' in a custom way or
        # we make UpsertMemoryTool take user_id as a hidden arg if possible.
        # Actually, if we use the standard ToolNode, we can't easily inject runtime config into __init__.
        # Alternate: 'user_id' is passed by LLM? No.

        # Let's use the pattern where we recreate the tool set for this user?
        # But the graph structure is static.

        # Standard solution: pass 'config' to tools?
        # LangChain tools accept 'config' in _arun if requested.

        # Let's stick to the plan:
        # "Bind UpsertMemory tool to the LLM".

        run_tools = list(tools)
        if store:
            configurable = config.get("configurable", {})
            user_id = configurable.get("user_id")
            guild_id = configurable.get("guild_id")
            channel_id = configurable.get("channel_id")

            if user_id:
                mem_tool = UpsertMemoryTool(store, user_id, guild_id, channel_id)
                run_tools.append(mem_tool)

        try:
            bound_llm = llm.bind_tools(run_tools)
        except Exception as e:
            # Fallback if LLM doesn't support binding (e.g. some Ollama models?)
            logger.warning(f"Tool binding FAILED: {e}")
            bound_llm = llm

        response = await bound_llm.ainvoke(messages, config)
        return {"messages": [response]}

    async def summarize_conversation(state: State, config: RunnableConfig):
        # Logic to summarize the conversation
        summary = state.get("summary", "")
        messages = state["messages"]

        # We'll keep the last 2 messages and summarize the rest
        if len(messages) > 6:
            to_summarize = messages[:-2]

            # Create a prompt for the summarization
            prompt = f"Distill the following conversation into a concise summary. Include important facts and context.\n\nCurrent summary: {summary}\n\nNew lines: {to_summarize}"

            # Call LLM to generate summary
            # We use the same LLM for summarization for simplicity
            response = await llm.ainvoke([HumanMessage(content=prompt)], config)
            new_summary = response.content

            # Delete the summarized messages
            delete_messages = [RemoveMessage(id=m.id) for m in to_summarize]

            return {"summary": new_summary, "messages": delete_messages}
        return {}

    def should_continue(
        state: State,
    ) -> Literal["tools", "summarize_conversation", END]:
        messages = state["messages"]
        last_message = messages[-1]

        if last_message.tool_calls:
            return "tools"

        # Check if we should summarize (e.g., if message count > 6)
        # Note: The 'summarize_conversation' node logic handles the splitting,
        # but we trigger it here.
        if len(messages) > 6:
            return "summarize_conversation"

        return END

    # Build Graph
    workflow = StateGraph(State)

    workflow.add_node("agent", call_model)

    # We need a custom tool node runner because standard ToolNode expects static tools
    # or we need to route to a dynamic tool node.
    # To keep it simple for this phase:
    # We will use valid "prebuilt" ToolNode but we need to ensure UpsertMemory is in it.
    # PROB: ToolNode is initialized ONCE at build time.
    # FIX: We can implement a custom node for "tools" that builds the tool list dynamically
    # OR we make UpsertMemoryTool accept user_id from the graph state/config context?
    # LangChain tools don't easy have access to RunnableConfig in _arun unless we jump hoops.

    # Pragmactic Fix:
    # Initialize ToolNode with the base tools.
    # Handle "upsert_memory" tool call MANUALLY in a separate node?
    # OR: use a custom function for the "tools" node.

    async def run_tools(state: State, config: RunnableConfig):
        tool_calls = state["messages"][-1].tool_calls
        results = []

        # Base tools map
        tool_map = {t.name: t for t in tools}

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            # Handle namespacing if present (e.g. default_api:upsert_memory)
            if ":" in tool_name:
                tool_name = tool_name.split(":")[-1]

            args = tool_call["args"]
            tool_call_id = tool_call["id"]

            output = None
            if tool_name == "upsert_memory" and store:
                # Handle memory tool specifically to inject user_id/guild_id/channel_id
                configurable = config.get("configurable", {})
                user_id = configurable.get("user_id")
                guild_id = configurable.get("guild_id")
                channel_id = configurable.get("channel_id")

                if user_id:
                    mem_tool = UpsertMemoryTool(store, user_id, guild_id, channel_id)
                    output = await mem_tool.ainvoke(args)
                else:
                    output = "Error: No user_id found in config."
            elif tool_name in tool_map:
                # Run standard tool
                output = await tool_map[tool_name].ainvoke(args)
            else:
                output = f"Error: Tool {tool_name} not found."

            results.append(
                {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": tool_name,
                    "content": str(output),
                }
            )
        return {"messages": results}

    workflow.add_node("tools", run_tools)
    workflow.add_node("summarize_conversation", summarize_conversation)

    workflow.add_edge(START, "agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )

    workflow.add_edge("tools", "agent")
    workflow.add_edge("summarize_conversation", END)

    return workflow.compile(checkpointer=checkpointer)
