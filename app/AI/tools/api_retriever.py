from typing import List, Dict
from langchain_core.tools import tool
from langchain_core.documents import Document
import yaml
import os


# 🔧 YAML 전체를 문서 형태가 아닌 문자열로 직접 반환
def extract_all_api_info(yaml_path: str) -> str:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    output = []
    for path, methods in data.get("paths", {}).items():
        for method, details in methods.items():
            summary = details.get("summary", "")
            responses = details.get("responses", {})
            parameters = details.get("parameters", [])

            inputs = [f"- {p.get('name')}: {p.get('description', '')}" for p in parameters]
            outputs = [f"- {code}: {r.get('description', '')}" for code, r in responses.items()]

            section = f"""### {method.upper()} {path}
설명: {summary or '없음'}
입력:
{chr(10).join(inputs) or '- 없음'}

출력:
{chr(10).join(outputs) or '- 없음'}
"""
            output.append(section)

    return "\n\n".join(output)


# ✅ 전체 API 내용을 단일 호출로 반환하는 툴
@tool
def get_full_api_info(file_path: str) -> Dict[str, str]:
    """
    전체 OpenAPI YAML 파일을 기반으로 모든 API 정보를 요약된 텍스트 형식으로 반환합니다.
    """
    return {"content": extract_all_api_info(file_path)}
