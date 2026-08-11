# Step 1: Define tools and model

from env_config import config

from langchain.tools import tool
from langchain.chat_models import init_chat_model


model = init_chat_model(
    "deepseek-chat",
    model_provider="openai",
    api_key=config.deepseek_api_key,
    base_url="https://api.deepseek.com",
    temperature=0
)


# Define tools
@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a / b


# Augment the LLM with tools
tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)

from langgraph.graph import add_messages
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolCall,
)
from langchain_core.messages import BaseMessage
from langgraph.func import entrypoint, task


# Step 2: Define model node

@task
def call_llm(messages: list[BaseMessage]):
    """LLM decides whether to call a tool or not"""
    return model_with_tools.invoke(
        [
            SystemMessage(
                content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
            )
        ]
        + messages
    )


# Step 3: Define tool node

@task
def call_tool(tool_call: ToolCall):
    """Performs the tool call"""
    tool = tools_by_name[tool_call["name"]]
    return tool.invoke(tool_call)


# Step 4: Define agent

@entrypoint()
def agent(messages: list[BaseMessage]):
    model_response = call_llm(messages).result()

    while True:
        if not model_response.tool_calls:
            break

        # Execute tools
        tool_result_futures = [
            call_tool(tool_call) for tool_call in model_response.tool_calls
        ]
        tool_results = [fut.result() for fut in tool_result_futures]
        messages = add_messages(messages, [model_response, *tool_results])
        model_response = call_llm(messages).result()

    messages = add_messages(messages, model_response)
    return messages

# Invoke
messages = [HumanMessage(content="Add 3 and 4.")]
for step in agent.stream(messages):
    for task_name, result in step.items():
        print(f"\n[Step Completed: {task_name}]")
        
        # If the result is a message or list of messages, print nicely
        if hasattr(result, "pretty_print"):
            result.pretty_print()
        elif isinstance(result, list):
            for item in result:
                if hasattr(item, "pretty_print"):
                    item.pretty_print()
                else:
                    print(item)
        else:
            print(result)