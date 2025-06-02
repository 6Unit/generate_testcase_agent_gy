import re
import os
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from AI.tools.api_retriever import get_full_api_info

class TestCaseGenerationAgent:
    display_name = "테스트 케이스 생성 에이전트"
    description = "요구사항 정의서를 기반으로 테스트 케이스를 생성하고, 구조화된 CSV로 저장합니다."
    category = "테스트 케이스 생성"
    features = "- 요구사항 기반 케이스 작성\n- 테스트 조건 및 예상 결과 포함"

    def __init__(self, temperature: float = 0.3, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(temperature=temperature, model=model, streaming=False)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "..", "prompts", "test_case_generation_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = PromptTemplate.from_template(f.read())

        self.output_csv_path = os.path.join(current_dir, "..", "data", "Tool_Shop_테스트케이스.csv")

        if os.path.exists(self.output_csv_path):
            os.remove(self.output_csv_path)
            print("🧹 기존 테스트 케이스 CSV 파일 초기화 완료")

        self.global_case_counter = 1

    def run(self, input_data: dict):
        input_text = input_data.get("input")
        file_path = input_data.get("file_path")
        yaml_path = input_data.get("yaml_path")

        if not input_text or not file_path or not yaml_path:
            raise ValueError("'input', 'file_path', 'yaml_path'는 필수입니다.")

        df = pd.read_csv(file_path)

        # ✅ 전체 요구사항 설명 통합
        full_requirement_text = "\n\n".join([
            f"[요구사항ID] {row['요구사항ID']}\n[요구사항명] {row['요구사항명']}\n[설명] {row['요구사항 설명']}"
            for _, row in df.iterrows() if str(row.get("요구사항 설명", "")).strip()
        ])

        print("[🔍 처리 중] 전체 요구사항 + API 정보 통합 완료")

        full_prompt = self.prompt_template.format(
            requirement_description=full_requirement_text,
            feature_name="전체 기능 목록 기반",
            importance="",
            role="",
            api_info = get_full_api_info.invoke({"file_path": yaml_path})["content"]
        )

        case_msg = self.llm.invoke(full_prompt)
        case_text = case_msg.content if hasattr(case_msg, "content") else str(case_msg)

        parsed_records = self._parse_test_cases(case_text)
        parsed_records = self._filter_duplicates(parsed_records)
        self._save_to_csv(parsed_records)
        return parsed_records

    def _parse_test_cases(self, text: str):
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

    def _filter_duplicates(self, records: list):
        seen = set()
        filtered = []
        for rec in records:
            key = rec["테스트 케이스 내용"]
            if key not in seen:
                seen.add(key)
                filtered.append(rec)
        return filtered

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
