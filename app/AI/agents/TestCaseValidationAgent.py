import os
import re
import pandas as pd
from openai import OpenAI
from AI.tools.source_scanner import scan_source_files
from AI.tools.keyword_extractor import extract_keywords

client = OpenAI()

class TestCaseValidationAgent:
    display_name = "테스트케이스 코드 검증 에이전트"
    description = "테스트케이스와 관련된 코드를 분석하여 LLM을 통해 테스트케이스를 재작성합니다."
    category = "테스트케이스 검증"
    features = "- 전체 필드 수정 LLM 위임\n- 키워드 기반 코드 추출\n- 로그 기반 추적"

    def __init__(self, source_dir: str, case_csv_path: str):
        self.source_dir = source_dir
        self.case_csv_path = case_csv_path

    def run(self) -> list[dict]:
        df = pd.read_csv(self.case_csv_path).fillna("")
        results = []

        for idx, row in df.iterrows():
            tc_no = row.get("No.", idx + 1)
            testcase = {
                "No": tc_no,
                "테스트 케이스 내용": str(row.get("테스트 케이스 내용", "")).strip(),
                "테스트 데이터": str(row.get("테스트 데이터", "")).strip(),
                "예상 결과": str(row.get("예상 결과", "")).strip()
            }

            keywords = extract_keywords(testcase)
            print(f"\n🔍 TC {tc_no} - 키워드: {keywords}")

            matched_code = scan_source_files(self.source_dir, keywords)
            total_hits = sum(len(lines) for lines in matched_code.values())
            print(f"    ✅ 코드 매칭됨: {len(matched_code)}개 파일, 총 {total_hits}건")

            actual_messages = self._extract_message_strings(matched_code)
            print(f"    💬 메시지 수: {len(actual_messages)}")

            # ✅ 무조건 LLM 호출
            revised_testcase = self._suggest_fix_with_llm(testcase, actual_messages, matched_code)

            print(f"    ✏️ 수정 완료:")
            print(f"       - 내용: {revised_testcase['테스트 케이스 내용']}")
            print(f"       - 데이터: {revised_testcase['테스트 데이터']}")
            print(f"       - 예상결과: {revised_testcase['예상 결과']}")

            results.append({
                "No": tc_no,
                "original_testcase": testcase,
                "final_testcase": revised_testcase,
                "matched_messages": actual_messages,
                "matched_code_summary": {
                    "files": len(matched_code),
                    "total_hits": total_hits,
                }
            })

        return results

    def _extract_message_strings(self, matched_code: dict) -> list[str]:
        message_set = set()
        for _, lines in matched_code.items():
            for _, line in lines:
                if any(x in line for x in ["{{", "}}", "t(", "t.", ".service", ".component", ".ts", ".vue", "./", "../"]):
                    continue
                if re.search(r"\w+\(.*\)", line): continue
                if re.search(r"[\?\{\}]", line): continue

                found = re.findall(r'"([^"]{4,})"', line)
                for msg in found:
                    msg = msg.strip()
                    if msg.startswith("/") or msg.startswith("http"):
                        continue
                    if re.fullmatch(r'[A-Za-z0-9_/-]+', msg):
                        continue
                    if len(re.findall(r'[가-힣a-zA-Z]', msg)) < 3:
                        continue
                    if msg.lower() in {"true", "false", "ok", "yes", "no"}:
                        continue
                    message_set.add(msg)
        return list(message_set)

    def _suggest_fix_with_llm(self, testcase: dict, actual_messages: list[str], matched_code: dict) -> dict:
        # 매칭된 코드 일부 샘플링
        code_snippets = []
        for file, lines in list(matched_code.items())[:3]:
            snippet = "\n".join([f"{os.path.basename(file)}:{lineno} → {line.strip()}" for lineno, line in lines[:2]])
            code_snippets.append(snippet)

        prompt = f"""
당신은 테스트 자동화 전문가입니다.

다음은 하나의 테스트케이스 정보와, 관련된 실제 코드 메시지 및 코드 일부입니다.  
테스트케이스 전체(내용, 테스트 데이터, 예상 결과)를 보완하여 다시 작성해주세요.

📌 작성 지침:
1. 전체 설명은 한국어로 작성합니다.
2. **"테스트 데이터"와 "예상 결과"에는 코드에서 사용된 메시지, 변수명, 형식 등을 그대로 사용**합니다.
3. 코드 메시지가 영어로 되어 있으므로, 테스트 데이터와 예상 결과는 반드시 영어 기반으로 표현해주세요.
4. 반환 형식은 반드시 JSON이어야 하며, 아래 형식을 따르세요.

[테스트 케이스 정보]
- 테스트 케이스 내용: {testcase["테스트 케이스 내용"]}
- 테스트 데이터: {testcase["테스트 데이터"]}
- 예상 결과: {testcase["예상 결과"]}

[코드에서 발견된 메시지들]
{chr(10).join(f"- {msg}" for msg in actual_messages)}

[매칭된 코드 일부]
{chr(10).join(code_snippets)}

💡 아래 형식으로만 반환하세요:

예시:
{{
  "테스트 케이스 내용": "사용자가 장바구니에 상품을 추가하고 결제하는 과정을 검증합니다.",
  "테스트 데이터": "productId=12345, quantity=1",
  "예상 결과": "결제 후 거래 내역에 해당 상품이 정상적으로 표시되어야 합니다."
}}
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            ).choices[0].message.content.strip()
            import json
            return json.loads(response)
        except Exception as e:
            print(f"⚠️ LLM 수정 실패 → 원본 사용: {e}")
            return testcase
