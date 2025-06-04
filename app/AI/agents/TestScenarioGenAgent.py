import re
import os
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


class TestScenarioGenerationAgent:
    display_name = "테스트 시나리오 생성 에이전트"
    description = "테스트 케이스 CSV 기반으로 시나리오를 생성하고, 구조화된 CSV로 저장합니다."
    category = "테스트 시나리오 생성"
    features = "- 시나리오 ID, 명칭, 상세 흐름, 검증 포인트 추출 및 저장"

    def __init__(self, temperature: float = 0.3, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(temperature=temperature, model=model, streaming=True)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "..", "prompts", "test_scenario_generation_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = PromptTemplate.from_template(f.read())

        self.case_csv_path = os.path.join(current_dir, "..", "data", "Tool_Shop_테스트케이스.csv")
        self.output_csv_path = os.path.join(current_dir, "..", "data", "Tool_Shop_통합테스트시나리오.csv")

        if os.path.exists(self.output_csv_path):
            os.remove(self.output_csv_path)
            print("🧹 기존 통합테스트시나리오 CSV 파일 초기화 완료")

    def run(self, input_data: dict):
        input_text = input_data.get("input")

        if not input_text:
            raise ValueError("'input' 필드는 필수입니다.")

        print(f"[Agent 실행] 입력: {input_text}")

        if not os.path.exists(self.case_csv_path):
            raise FileNotFoundError("테스트 케이스 CSV가 존재하지 않습니다.")
        case_df = pd.read_csv(self.case_csv_path)
        case_list = [f"{row['No.']} {row['테스트 케이스 내용']}" for _, row in case_df.iterrows() if 'No.' in row and '테스트 케이스 내용' in row]
        case_text_block = "\n".join(case_list)

        print("[LLM 통화] 전체 테스트케이스 기반의 시나리오 생성")
        full_prompt = self.prompt_template.format(test_case_list=case_text_block)
        scenario_msg = self.llm.invoke(full_prompt)
        scenario_text = scenario_msg.content if hasattr(scenario_msg, "content") else str(scenario_msg)

        print("💾 시나리오 원문:\n", scenario_text)

        parsed_rows = self._parse_scenario_text(scenario_text)
        self._save_to_csv(parsed_rows)

        result_text = "\n".join([
            f"{i+1}. {r['시나리오명']} ({r['시나리오 ID']})"
            for i, r in enumerate(parsed_rows)
        ])
        print(f"\n✅ 전체 시나리오 요약:\n{result_text}")
        return result_text

    def _parse_scenario_text(self, text: str):
        records = []

        for line in text.splitlines():
            if '|' not in line:
                continue

            parts = [p.strip() for p in line.split('|')]
            if len(parts) != 4:
                continue

            if parts[0].lower().startswith("\uc2dc\ub098\ub9ac\uc624 id") or parts[1].lower().startswith("\uc2dc\ub098\ub9ac\uc624\uba54"):
                continue

            scenario_id, name, flow, raw_checks = parts
            check_items = [item.strip() for item in raw_checks.split('\\') if item.strip()]
            numbered_checks = "\n".join([f"{i+1}. {item}" for i, item in enumerate(check_items)])

            records.append({
                "시나리오 ID": scenario_id,
                "시나리오명": name,
                "상세설명(흐름도)": flow,
                "검증포인트": numbered_checks
            })

        return records

    def _save_to_csv(self, records: list):
        df_new = pd.DataFrame(records)

        if os.path.exists(self.output_csv_path):
            df_existing = pd.read_csv(self.output_csv_path)
            df_existing = df_existing[~df_existing["\uc2dc\ub098\ub9ac오 ID"].isin(df_new["\uc2dc\ub098\ub9ac오 ID"])]
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        df_combined.to_csv(self.output_csv_path, index=False, encoding="utf-8-sig")
        print(f"📁 구조화된 시나리오가 저장되었습니다: {self.output_csv_path}")
