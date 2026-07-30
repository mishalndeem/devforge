import os
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

load_dotenv()


class AgentState(TypedDict):
    message: str
    category: Literal["support", "unrelated"]
    reply: str


def get_llm():
    api_key = os.getenv("OLLAMA_API_KEY")
    model_name = os.getenv("OLLAMA_MODEL")

    if not api_key:
        raise ValueError("OLLAMA_API_KEY is missing.")

    if not model_name:
        raise ValueError("OLLAMA_MODEL is missing.")

    return ChatOllama(
        model=model_name,
        base_url="https://ollama.com",
        temperature=0.4,
        client_kwargs={
            "headers": {
                "Authorization": f"Bearer {api_key}"
            }
        },
    )


def classify_question(state: AgentState):
    message = state["message"].lower()

    support_words = [
        "devforge",
        "internship",
        "certificate",
        "task",
        "assignment",
        "python",
        "fastapi",
        "langchain",
        "langgraph",
        "ai",
        "web development",
        "deployment",
        "render",
        "github",
        "project",
    ]

    is_related = any(word in message for word in support_words)

    if is_related:
        return {
            "message": state["message"],
            "category": "support",
            "reply": "",
        }

    return {
        "message": state["message"],
        "category": "unrelated",
        "reply": "",
    }


def route_question(state: AgentState):
    return state["category"]


def support_agent(state: AgentState):
    llm = get_llm()

    system_prompt = """
You are DEVFORGE Student Support AI Agent.

You help students with DEVFORGE internships, AI Engineering,
Web Development, Python, FastAPI, LangChain, LangGraph,
student projects, GitHub, Render deployment, assignments,
and general technical learning guidance.

Rules:
- Give clear, practical, student-friendly answers.
- Keep answers concise but helpful.
- Do not invent DEVFORGE deadlines, fees, certificate policies, or rules.
- If exact information is unavailable, tell the student to contact DEVFORGE support.
- Do not answer unrelated questions.
"""

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["message"]),
        ]
    )

    return {
        "message": state["message"],
        "category": "support",
        "reply": response.content,
    }


def unrelated_response(state: AgentState):
    return {
        "message": state["message"],
        "category": "unrelated",
        "reply": (
            "I am DEVFORGE Student Support AI Agent. "
            "I can help with DEVFORGE internships, AI Engineering, "
            "Web Development, Python, LangChain, LangGraph, "
            "assignments, and deployment guidance."
        ),
    }


workflow = StateGraph(AgentState)

workflow.add_node("classify_question", classify_question)
workflow.add_node("support_agent", support_agent)
workflow.add_node("unrelated_response", unrelated_response)

workflow.set_entry_point("classify_question")

workflow.add_conditional_edges(
    "classify_question",
    route_question,
    {
        "support": "support_agent",
        "unrelated": "unrelated_response",
    },
)

workflow.add_edge("support_agent", END)
workflow.add_edge("unrelated_response", END)

agent_graph = workflow.compile()


def run_agent(message: str):
    result = agent_graph.invoke(
        {
            "message": message,
            "category": "support",
            "reply": "",
        }
    )

    return {
        "reply": result["reply"],
        "category": result["category"],
    }
