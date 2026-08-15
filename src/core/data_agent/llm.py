import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from env_config import config

from langchain.tools import tool
from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from typing_extensions import Literal
from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import json
from vnstock import Market, Reference

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
    final_answer: str
#route schema
class Route(BaseModel):
    step: Literal["normal answer","market data summary"] = Field(None)

#Message input
message = ""


#classify intent llm
def classify_intent_node(state: State):
    res = llm.invoke(
        [
            SystemMessage(
                content="""Route the input to either 'normal answer' or 'market data summary' based on the user's request. 
Output ONLY a JSON object exactly matching this format: {"step": "normal answer"} or {"step": "market data summary"}"""
            ),
            HumanMessage(content=state["input"]),
        ]
    )
    try:
        raw = res.content.strip("` \n")
        if raw.startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        intent = data.get("step", "normal answer")
    except Exception:
        intent = "normal answer"
        
    return {"intent": intent}

def choose_api_node(state: State):
    res = llm.invoke(
        [
            SystemMessage(content="""Determine which API to call based on the user request. 
APIs available:
- 'company_info': for company profile/info. Parameters: symbol (e.g. FPT)
- 'historical_prices': for OHLCV price history. Parameters: symbol, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD)
- 'none': if no API needed

Output ONLY a JSON object exactly matching this format, with empty strings if not applicable:
{"api_name": "...", "symbol": "...", "start_date": "...", "end_date": "..."}"""),
            HumanMessage(content=state["input"])
        ]
    )
    try:
        raw = res.content.strip("` \n")
        if raw.startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        api_chosen = json.dumps(data)
    except Exception:
        api_chosen = '{"api_name": "none"}'
        
    return {"api_chosen": api_chosen}

def call_api_node(state: State):
    req_dict = json.loads(state.get("api_chosen", "{}"))
    api_name = req_dict.get("api_name")
    symbol = req_dict.get("symbol")
    
    if api_name == "company_info" and symbol:
        ref = Reference()
        df = ref.company(symbol=symbol).info() if callable(ref.company) else ref.company.info(symbol=symbol)
        res = df.to_json(orient="records")
    elif api_name == "historical_prices" and symbol:
        market = Market()
        start = req_dict.get("start_date")
        end = req_dict.get("end_date")
        df = market.equity(symbol=symbol).ohlcv(start=start, end=end) if callable(market.equity) else market.equity.ohlcv(symbol=symbol, start=start, end=end)
        res = df.to_json(orient="records")
    else:
        res = '{"error": "No valid API or parameters found."}'
        
    return {"json_result": res}

def extract_result_node(state: State):
    # For now, simply pass the JSON as cleaned result. 
    return {"cleaned_result": state.get("json_result", "")}

def summarize_aggregate_node(state: State):
    # Use LLM to summarize the extracted data
    summary = llm.invoke(
        [
            SystemMessage(content="Summarize the following market data in a clear, concise manner."),
            HumanMessage(content=f"Data: {state.get('cleaned_result')}\nUser request: {state.get('input')}")
        ]
    )
    return {"summarized_result": summary.content}

def answer_node(state: State):
    if state.get("intent") == "market data summary":
        final = state.get("summarized_result", "")
    else:
        final = llm.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=state.get("input", ""))
        ]).content
    return {"final_answer": final}

def other_node(state: State):
    # Handle the normal response path if needed
    return {}

def route_intent(state: State) -> str:
    if state.get("intent") == "market data summary":
        return "choose_api"
    else:
        return "other"

# Build the graph
workflow = StateGraph(State)

workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("choose_api", choose_api_node)
workflow.add_node("call_api", call_api_node)
workflow.add_node("extract_result", extract_result_node)
workflow.add_node("summarize_aggregate", summarize_aggregate_node)
workflow.add_node("other", other_node)
workflow.add_node("answer", answer_node)

workflow.add_edge(START, "classify_intent")
workflow.add_conditional_edges(
    "classify_intent",
    route_intent,
    {
        "choose_api": "choose_api",
        "other": "other"
    }
)
workflow.add_edge("choose_api", "call_api")
workflow.add_edge("call_api", "extract_result")
workflow.add_edge("extract_result", "summarize_aggregate")
workflow.add_edge("summarize_aggregate", "answer")
workflow.add_edge("other", "answer")
workflow.add_edge("answer", END)

app = workflow.compile()

result = app.invoke({"input": "give me VNINDEX rate at 2024-10-10"})
import sys
sys.stdout.reconfigure(encoding='utf-8')
print(result["final_answer"])