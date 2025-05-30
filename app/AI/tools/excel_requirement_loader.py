from typing import List, Dict
from langchain_core.tools import tool
import pandas as pd


@tool
def requirement_excel_loader(file_path: str) -> str:
    """
    요구사항 정의서 CSV 파일을 전체 로드하여 기능 추출용 텍스트로 반환합니다.
    각 요구사항명 + 설명을 하나의 텍스트로 구성하여 반환합니다.
    """
    df = pd.read_csv(file_path, encoding="utf-8")

    if "요구사항 설명" not in df.columns or "요구사항명" not in df.columns:
        raise ValueError("'요구사항 설명'과 '요구사항명' 열이 존재해야 합니다.")

    texts = []
    for _, row in df.iterrows():
        title = row.get("요구사항명", "")
        desc = row.get("요구사항 설명", "")
        line = f"{title}: {desc}"
        texts.append(line)

    full_text = "\n".join(texts)
    return full_text


# 이름, 설명 지정 (선택)
requirement_excel_loader.name = "requirement_excel_loader"
requirement_excel_loader.description = (
    "요구사항 정의서 CSV에서 전체 내용을 읽어 분석 가능한 텍스트로 반환합니다. "
    "요구사항명과 설명을 기반으로 LLM이 기능을 도출할 수 있도록 합니다."
)
