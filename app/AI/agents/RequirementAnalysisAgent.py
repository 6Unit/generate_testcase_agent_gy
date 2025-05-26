from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import os
from app.AI.tools.excel_requirement_loader import requirement_excel_loader


class RequirementAnalysisAgent:
    display_name = "요구사항 분석 에이전트"
    description = (
        "요구사항 문서를 기반으로 핵심 기능 리스트를 도출하는 에이전트입니다. "
        "엑셀 문서를 직접 읽어 문서 전체 내용을 기반으로 기능을 간결하게 추출합니다."
    )
    category = "요구사항 분석"
    features = "- 요구사항 문서 이해\n- 핵심 기능 항목 도출\n- 간결한 리스트 제공"

    def __init__(self, temperature: float = 0.3, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(temperature=temperature, model=model, streaming=True)

        # 프롬프트 템플릿 로딩
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.abspath(os.path.join(current_dir, "..", "prompts", "requirement_analysis_prompt.txt"))
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_str = f.read()

        self.prompt_template = PromptTemplate.from_template(prompt_str)

    def run(self, input_data: dict):
        input_text = input_data.get("input")
        file_path = input_data.get("file_path")

        if not input_text or not file_path:
            raise ValueError("'input'과 'file_path' 키가 모두 필요합니다.")

        print(f"[Agent 실행] 입력: {input_text}")

        # ✅ 엑셀 로더 툴 직접 실행
        document_text = requirement_excel_loader.invoke({"file_path": file_path})

        # ✅ 프롬프트 채우기
        full_prompt = self.prompt_template.format(document=document_text)

        # ✅ LLM 실행
        result = self.llm.invoke(full_prompt)

        print(f"[Agent 실행 결과] 결과:\n{result}")
        return result
