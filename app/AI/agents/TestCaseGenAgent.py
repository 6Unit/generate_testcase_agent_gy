import re
import os
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from AI.tools.api_retriever import yaml_search


class TestCaseGenerationAgent:
    display_name = "테스트 케이스 생성 에이전트"
    description = "요구사항 정의서를 기반으로 테스트 케이스를 생성하고, 구조화된 CSV로 저장합니다."
    category = "테스트 케이스 생성"
    features = "- 요구사항 기반 케이스 작성\n- 테스트 조건 및 예상 결과 포함"

    def __init__(self, temperature: float = 0.3, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(temperature=temperature, model=model, streaming=True)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "..", "prompts", "test_case_generation_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = PromptTemplate.from_template(f.read())

        self.output_csv_path = os.path.join(current_dir, "..", "data", "Tool_Shop_테스트케이스.csv")

        # ✅ 기존 파일 초기화
        if os.path.exists(self.output_csv_path):
            os.remove(self.output_csv_path)
            print("🧹 기존 테스트 케이스 CSV 파일 초기화 완료")

        self.global_case_counter = 1  # 전체 테스트 케이스 번호 전역 카운터

    def run(self, input_data: dict):
        input_text = input_data.get("input")
        file_path = input_data.get("file_path")
        yaml_path = input_data.get("yaml_path")  # ✅ API 명세 경로 추가

        if not input_text or not file_path or not yaml_path:
            raise ValueError("'input', 'file_path', 'yaml_path'는 필수입니다.")

        df = pd.read_csv(file_path)
        parsed_records = []

        for idx, row in df.iterrows():
            requirement_desc = str(row.get("요구사항 설명", "")).strip()
            feature_name = str(row.get("요구사항명", "")).strip()
            importance = str(row.get("중요도", "")).strip()
            role = str(row.get("역할", "")).strip()

            if not requirement_desc:
                continue

            # ✅ API 정보 검색
            tool_result = yaml_search.invoke({
                "query": feature_name,
                "file_path": yaml_path
            })
            api_info = "\n".join([r["content"] for r in tool_result]) or "관련 API 없음"

            print(f"[🔍 처리 중] {feature_name} - 관련 API 정보 반영 완료")

            # 프롬프트 구성
            full_prompt = self.prompt_template.format(
                requirement_description=requirement_desc,
                feature_name=feature_name + "\n\n[관련 API 정보]\n" + api_info,
                importance=importance,
                role=role
            )

            case_msg = self.llm.invoke(full_prompt)
            case_text = case_msg.content if hasattr(case_msg, "content") else str(case_msg)

            parsed = self._parse_test_cases(case_text)
            if parsed:
                parsed_records.extend(parsed)

        self._save_to_csv(parsed_records)
        return parsed_records

    def _parse_test_cases(self, text: str):
        # ✅ '|' 기준 파싱
        lines = [line.strip() for line in text.splitlines() if line.strip() and '|' in line]
        records = []

        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5 and parts[0].isdigit():
                records.append({
                    "No.": self.global_case_counter,
                    "테스트 케이스 내용": parts[1],
                    "사전조건": parts[2],
                    "테스트 데이터": parts[3],
                    "예상 결과": parts[4]
                })
                self.global_case_counter += 1

        return records

    def _save_to_csv(self, records: list):
        if not records:
            print("⚠️ 저장할 레코드가 없습니다.")
            return

        df_new = pd.DataFrame(records)

        if os.path.exists(self.output_csv_path):
            df_existing = pd.read_csv(self.output_csv_path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        df_combined.to_csv(self.output_csv_path, index=False, encoding="utf-8-sig")
        print(f"📁 구조화된 테스트 케이스가 저장되었습니다: {self.output_csv_path}")
