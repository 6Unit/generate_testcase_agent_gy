import re
import ast
from openai import OpenAI

client = OpenAI()

def extract_keywords(testcase: dict) -> list[str]:
    # 1단계: 한국어 키워드 추출
    context = "\n".join([
        f"테스트 케이스 설명: {testcase.get('테스트 케이스 내용', '')}",
        f"예상 결과: {testcase.get('예상 결과', '')}"
    ])

    extract_prompt = f"""
아래 테스트 케이스 설명과 예상 결과로부터 핵심 기능을 대표하는 3~5개의 한국어 키워드를 추출하세요.
이 키워드는 코드 검색을 위한 주요 의미 단서로 사용됩니다.

{context}

- 반환 형식: ["키워드1", "키워드2", ...]
- 설명 없이 리스트 형태만 출력하세요.
"""
    try:
        response_ko = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": extract_prompt}],
            temperature=0.3,
        ).choices[0].message.content.strip()

        keyword_list_ko = ast.literal_eval(response_ko)
    except Exception:
        return []

    # 2단계: 유의어 확장
    synonym_map = {
        "거래": ["거래", "주문", "송장"],
        "문의": ["문의", "연락", "고객지원", "메시지"],
        "상세": ["상세", "정보", "내용"],
        "조회": ["조회", "불러오기", "가져오기"],
        "추가": ["추가", "등록", "생성"],
        "삭제": ["삭제", "제거"],
        "수정": ["수정", "변경"],
        "포함": ["포함", "리스트에 있음"],
    }

    expanded_ko = []
    for kw in keyword_list_ko:
        expanded_ko.extend(synonym_map.get(kw.strip(), [kw.strip()]))

    # 3단계: 영어 번역
    ko_string = ", ".join(set(expanded_ko))
    translate_prompt = f"""
다음 한국어 키워드들을 자연스러운 영어로 간결하게 번역하세요. 결과는 쉼표(,)로 구분된 하나의 영어 키워드 목록입니다.

{ko_string}

- 예: profile view, success message, after login
- 설명 없이 결과만 출력하세요.
"""
    try:
        response_en = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": translate_prompt}],
            temperature=0.3,
        ).choices[0].message.content.strip()
    except Exception:
        return []

    # 4단계: 정제 및 필터링
    raw_keywords = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', response_en)
    filtered_keywords = [
        kw.lower() for kw in raw_keywords
        if len(kw) >= 4 and kw.lower() not in {
            "user", "data", "info", "test", "input", "value", "page", "screen", "click", "view", "import"
        }
    ]

    # # ✅ 5단계: 범용 키워드 병합
    # common_keywords = [
    #     "required", "invalid", "success", "error", "confirm", "submit",
    #     "login", "register", "update", "delete", "message", "notfound"
    # ]
    
    # ✅ 최종 키워드 결과
    return sorted(set(filtered_keywords))
