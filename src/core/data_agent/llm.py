from env_config import config

from langchain.tools import tool
from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from typing_extensions import Literal
from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

llm = init_chat_model(
    "deepseek-chat",
    model_provider="openai",
    api_key=config.deepseek_api_key,
    base_url="https://api.deepseek.com",
    temperature=0
)

#state
class State(TypedDict):
    input: str
    intent: str
    api_chosen: str
    json_result: str
    cleaned_result: str
    summarized_result: str
#route schema
class Route(BaseModel):
    step: Literal["normal answer","market data summary"] = Field(None)

#Message input
message = ""

# Augment the LLM with schema for structured output
router = llm.with_structured_output(Route)


#classify intent llm
def classify_intent_llm(state: State):
    intent = router.invoke(
        [
            SystemMessage(
                content="Route the input to normal info answer or market data retrieval, summary based on the user's request."
            ),
            HumanMessage(content=state["input"]),
        ]
    )