import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from graph.state import StudyRoadmap, Topic

load_dotenv()

MODEL_NAME = os.getenv("LMSTUDIO_MODEL", "qwen2.5-7b-instruct")
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")


PLANNER_SYSTEM_PROMPT = """You are an expert curriculum designer. Your job is to
create a structured study roadmap when given a learning goal.

Return ONLY valid JSON with no prose, no markdown code fences, no explanation.
The JSON must match this exact schema:

{
  "goal": "the original learning goal exactly as given",
  "total_weeks": <integer between 1 and 12>,
  "weekly_hours": <integer between 3 and 10>,
  "topics": [
    {
      "title": "Short topic name (3-6 words)",
      "description": "One clear sentence explaining what this topic covers",
      "estimated_minutes": <integer between 30 and 120>,
      "prerequisites": ["title of earlier topic if required, else empty list"],
      "status": "pending"
    }
  ]
}

Rules:
- Order topics from foundational to advanced
- prerequisites must reference earlier topic titles exactly as written
- estimated_minutes is time for one focused study session, not total time
- Aim for 4 to 6 topics, enough depth without being overwhelming
- Every topic must have a clear, specific description
- status must always be "pending"
"""


def build_planner_llm() -> ChatOpenAI:
    """Tạo client ChatOpenAI để kết nối với LM Studio Local Server.

    - base_url: Cổng local mặc định của LM Studio (cần có `/v1` ở cuối).
    - api_key: LM Studio không yêu cầu key, nhưng client bắt buộc truyền một
    chuỗi bất kỳ để tránh lỗi validation.
    - model_kwargs={"response_format": {"type": "json_object"}}: Ép model xuất
    định dạng JSON.
    """
    return ChatOpenAI(
        base_url=LMSTUDIO_BASE_URL,
        api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
        model=MODEL_NAME,
        temperature=0.1,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def parse_roadmap_json(json_string: str) -> StudyRoadmap:
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(
            "LLM returned invalid JSON.\n"
            f"Error: {e}\n"
            f"Raw output (first 300 chars): {json_string[:300]}"
        )

    # Validate required top-level fields
    required = ["goal", "total_weeks", "topics"]
    for field in required:
        if field not in data:
            raise ValueError(f"LLM JSON missing required field: '{field}'")

    if not isinstance(data["topics"], list) or len(data["topics"]) == 0:
        raise ValueError("LLM JSON 'topics' must be a non-empty list")

    # Build Topic objects
    topics = []
    for i, t in enumerate(data["topics"]):
        # Validate each topic has required fields
        for field in ["title", "description", "estimated_minutes"]:
            if field not in t:
                raise ValueError(
                    f"Topic {i} missing required field: '{field}'"
                )
        topics.append(Topic(
            title=t["title"],
            description=t["description"],
            estimated_minutes=int(t["estimated_minutes"]),
            prerequisites=t.get("prerequisites", []),
            status=t.get("status", "pending"),
        ))

    return StudyRoadmap(
        goal=data["goal"],
        total_weeks=int(data["total_weeks"]),
        weekly_hours=int(data.get("weekly_hours", 5)),
        topics=topics,
    )

def generate_study_roadmap(goal: str) -> StudyRoadmap:
    """Generate a study roadmap for a given learning goal.

    Args:
        goal (str): The learning goal to create a roadmap for.  

    Returns:
        StudyRoadmap: The generated study roadmap.
    """
    llm = build_planner_llm()
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"Create a study roadmap for: {goal}")
    ]

    print(f"[Curriculum Planner] Calling {MODEL_NAME}...")
    try:
        response = llm.invoke(messages)
    except Exception as e:
        print(f"[Curriculum Planner] LLM call failed: {e}")
        return {
            "error": f"LLM call failed: {e}",
            "messages": messages,
        }
    
    try:
        roadmap = parse_roadmap_json(response.content)
    except ValueError as e:
        print(f"[Curriculum Planner] Parse error: {e}")
        # Return error state, the graph can route to an error handler
        return {
            "error": str(e),
            "messages": messages + [response],
        }
    
    return {
        "roadmap": roadmap,
        "messages": messages + [response],
        "error": None,
    }