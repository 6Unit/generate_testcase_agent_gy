import sys
import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from typing import TypedDict, Dict, Any, List

# ✅ 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ✅ 모듈 import
from app.AI.agents.RequirementAnalysisAgent import RequirementAnalysisAgent
from app.AI.tools.excel_requirement_loader import requirement_excel_loader


# ✅ 상태 정의
class AgentState(TypedDict):
    input: str
    file_path: str
    output: str


# ✅ 분석 노드
def run_analysis(state: AgentState) -> Dict[str, Any]:
    agent = RequirementAnalysisAgent()
    prompt = f"{state['input']}\nfile_path={state['file_path']}"
    result = agent.run({
        "input": state["input"],
        "file_path": state["file_path"]
    })



    if isinstance(result, dict) and "output" in result:
        return {"output": result["output"]}
    return {"output": result}


# ✅ 그래프 구성
def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("run_analysis", run_analysis)
    builder.set_entry_point("run_analysis")
    builder.set_finish_point("run_analysis")
    return builder.compile()


# ✅ 실행
if __name__ == "__main__":
    load_dotenv()

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CSV_PATH = os.path.join(BASE_DIR, "app", "AI", "data", "요구사항정의서_v0.1.csv")

    graph = build_graph()
    result = graph.invoke({
        "input": "요구사항 정의서를 바탕으로 핵심 기능을 항목별로 나열해줘.",
        "file_path": CSV_PATH
    })

    print("\n✅ 에이전트 출력 결과:\n")
    print(result["output"])
