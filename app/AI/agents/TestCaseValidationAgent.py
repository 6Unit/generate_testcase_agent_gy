import os
import re
import json
import pandas as pd
from openai import OpenAI
from AI.tools.source_scanner import scan_source_files
from AI.tools.keyword_extractor import extract_keywords

client = OpenAI()

class TestCaseValidationAgent:
    display_name = "테스트케이스 코드 검증 에이전트"
    description = "테스트케이스와 관련된 코드를 분석하여 LLM을 통해 테스트케이스를 재작성하고 CSV에 반영합니다."
    category = "테스트케이스 검증"
    features = "- 전체 필드 수정 LLM 위임\n- 키워드 기반 코드 추출\n- 로그 기반 추적 및 CSV 반영"

    def __init__(self, source_dir: str, case_csv_path: str):
        self.source_dir = source_dir
        self.case_csv_path = case_csv_path

    def run(self) -> list[dict]:
        df = pd.read_csv(self.case_csv_path).fillna("")
        results = []
        revised_rows = []

        for idx, row in df.iterrows():
            tc_no = row.get("No.", idx + 1)
            testcase = {
                "No": tc_no,
                "테스트 케이스 내용": str(row.get("테스트 케이스 내용", "")).strip(),
                "사전조건": str(row.get("사전조건", "")).strip(),
                "테스트 데이터": str(row.get("테스트 데이터", "")).strip(),
                "예상 결과": str(row.get("예상 결과", "")).strip()
            }

            keywords = extract_keywords(testcase)
            print(f"\n🔍 TC {tc_no} - 키워드: {keywords}")

            matched_code = scan_source_files(self.source_dir, keywords)
            total_hits = sum(len(lines) for lines in matched_code.values())
            print(f"📁 코드 매칭: {len(matched_code)}개 파일 (총 {total_hits}건)")

            actual_messages = self._extract_message_strings(matched_code)
            print(f"💬 메시지 수: {len(actual_messages)}")

            revised_testcase = self._suggest_fix_with_llm(testcase, actual_messages, matched_code)

            print(f"✏️ 수정 완료: {revised_testcase}")

            revised_rows.append({
                "No.": tc_no,
                "테스트 케이스 내용": revised_testcase["테스트 케이스 내용"],
                "사전조건": row.get("사전조건", ""),
                "테스트 데이터": revised_testcase["테스트 데이터"],
                "예상 결과": revised_testcase["예상 결과"]
            })

            results.append({
                "No": tc_no,
                "original_testcase": testcase,
                "final_testcase": revised_testcase,
            })

        pd.DataFrame(revised_rows).to_csv(self.case_csv_path, index=False, encoding="utf-8-sig")
        print(f"\n📁 수정된 테스트케이스 CSV 저장 완료: {self.case_csv_path}")
        return results

    def _extract_message_strings(self, matched_code: dict) -> list[str]:
        message_set = set()
        for _, lines in matched_code.items():
            for _, line in lines:
                if any(x in line for x in ["{{", "}}", "t(", "t.", ".ts", ".vue"]): continue
                if re.search(r"\w+\(.*\)", line): continue
                found = re.findall(r"[\"']([^\"']{4,})[\"']", line)
                for msg in found:
                    if not re.search(r'[가-힣a-zA-Z]{3,}', msg): continue
                    message_set.add(msg.strip())
        return list(message_set)

    def _suggest_fix_with_llm(self, testcase: dict, actual_messages: list[str], matched_code: dict) -> dict:
        code_snippets = []
        for file, lines in list(matched_code.items())[:2]:
            snippet_header = f"📁 {os.path.basename(file)}"
            snippet_lines = "\n".join([f"  {lineno}: {line}" for lineno, line in lines[:2]])
            code_snippets.append(f"{snippet_header}\n{snippet_lines}")
        code_snippet_text = "\n".join(code_snippets)
        message_text = "\n".join(f"- {msg}" for msg in actual_messages[:10]) or "(없음)"

        prompt = f"""
당신은 테스트 자동화 전문가입니다.

다음은 테스트케이스 설명과 코드 분석 결과입니다.
이 테스트케이스는 실제 코드의 동작과 메시지를 바탕으로 **현실적인 테스트 항목**으로 수정되어야 합니다.

🔧 작업 목표:
- 테스트 목적과 절차가 명확하게 드러나도록 소스코드 토대로 설명을 보완하거나 수정하세요.
- 테스트 절차는 핵심 흐름만 간결하게 요약된 한 문장이어야 합니다.
- 테스트 데이터는 실제 사용자의 입력 또는 API 요청에서 사용될 수 있는 형식으로 작성하세요.
- 예상 결과는 사용자 인터페이스(UI)나 API 응답에서 실제로 **확인 가능한 메시지나 상태**만 포함하세요.
- 예상 결과는 반드시 코드에서 추출된 메시지 중에서 선택하거나 조합하여 작성하세요.
- 테스트 데이터는 **실제 코드 변수명 그대로** 작성해야 하며, 자연어 표현(예: "상품 ID", "이메일")은 금지합니다.
- 테스트 데이터에는 코드에서 확인되지 않는 항목을 포함하지 마세요.
- 내부 경로나 i18n 키(`pages.xx.xx`, `app-login`, `t("...")`) 등은 제외하세요.
- 반환 형식은 반드시 아래 JSON 구조로 출력하고, 불필요한 설명은 포함하지 마세요.


📌 예시:
기존 테스트케이스:
- 내용: 로그인 시도 후 성공 여부 확인
- 테스트 데이터: email=admin@example.com, password=1234
- 예상 결과: 로그인 성공

💬 코드 메시지: 
- Login success
- Invalid email or password

🧩 코드 일부:
📁 AuthService.ts
  34: if (success) showMessage("Login success");
📁 AuthService.ts
  37: else showMessage("Invalid email or password");

📤 출력 예시:
{{
  "테스트 케이스 내용": "사용자가 이메일과 비밀번호를 입력하여 로그인 후, 성공 여부를 확인하는 테스트",
  "테스트 데이터": "email=admin@example.com, password=1234",
  "예상 결과": "'Login success' 메시지가 출력되어야 하며, 실패 시 'Invalid email or password' 메시지가 출력되어야 함"
}}


📌 기존 테스트케이스:
- 내용: {testcase["테스트 케이스 내용"]}
- 사전조건: {testcase["사전조건"]}
- 테스트 데이터: {testcase["테스트 데이터"]}
- 예상 결과: {testcase["예상 결과"]}

🔧 주의:
- 테스트는 반드시 **사전조건이 모두 만족된 상태**에서 실행됩니다.
- 예: 사용자가 로그인된 상태라는 사전조건이 있는 경우, 다시 로그인하지 않습니다.

💬 코드에서 발견된 메시지:
{message_text}

🧩 코드 분석 결과 (일부):
{code_snippet_text}

📤 아래 형식으로 정확하게 출력하세요 (JSON만 반환):
{{
"테스트 케이스 내용": "여기에 전체 테스트 목적과 흐름을 요약하세요",
"사전조건": "테스트 실행 전에 충족되어야 할 구체적인 조건 (예: 로그인 상태)",
"테스트 데이터": "key1=value1, key2=value2",
"예상 결과": "어떤 메시지가 출력되어야 하는지, 상태가 어떤지"
}}
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            ).choices[0].message.content.strip()
            return json.loads(response)
        except Exception as e:
            print(f"⚠️ LLM 수정 실패 → 원본 사용: {e}")
            return testcase
