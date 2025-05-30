import sys
import os
import time
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from typing import TypedDict, Dict, Any
from AI.agents.TestScenarioGenAgent import TestScenarioGenerationAgent
from AI.agents.TestCaseGenAgent import TestCaseGenerationAgent

# ✅ 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ✅ 기본 경로 및 파일 상수
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENT_CSV_PATH = os.path.join(BASE_DIR, "app", "AI", "data", "Tool_Shop_요구사항정의서.csv")
SCENARIO_CSV_PATH = os.path.join(BASE_DIR, "app", "AI", "data", "Tool_Shop_통합테스트시나리오.csv")
YAML_PATH = os.path.join(BASE_DIR, "app", "AI", "data", "Tool_Shop_api.yaml")

# ✅ 상태 정의
class AgentState(TypedDict):
    input: str
    file_path: str
    output: str

# ✅ 테스트 케이스 생성 노드 (요구사항 기반)
def run_test_case_generation(state: AgentState) -> Dict[str, Any]:
    agent = TestCaseGenerationAgent()
    agent.run({
        "input": state["input"],
        "file_path": state["file_path"],
        "yaml_path": YAML_PATH
    })
    return {"output": "테스트 케이스 생성 완료"}

# ✅ 시나리오 생성 노드 (요구사항 기반)
def run_scenario_generation(state: AgentState) -> Dict[str, Any]:
    agent = TestScenarioGenerationAgent()
    result = agent.run({
        "input": state["input"],
        "file_path": state["file_path"]
    })
    return {"output": result}

# ✅ 그래프 구성
def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("run_test_case_generation", run_test_case_generation)
    builder.add_node("run_scenario_generation", run_scenario_generation)

    builder.set_entry_point("run_test_case_generation")
    builder.add_edge("run_test_case_generation", "run_scenario_generation")
    builder.set_finish_point("run_scenario_generation")

    return builder.compile()

# ✅ 실행
if __name__ == "__main__":
    load_dotenv()

    graph = build_graph()
    start_time = time.time()  # ⏱️ 시작 시간 측정
    result = graph.invoke({
        "input": "요구사항 정의서를 바탕으로 테스트 케이스들을 생성해줘.",
        "file_path": REQUIREMENT_CSV_PATH
    })

    end_time = time.time()  # ⏱️ 종료 시간 측정
    # 시간 계산
    elapsed = end_time - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    # 결과 출력
    print("\n✅ 최종 테스트 시나리오 생성 결과:\n")
    print(result["output"])
    print(f"\n🕒 총 소요 시간: {minutes}분 {seconds}초")
