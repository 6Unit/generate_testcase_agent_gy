from typing import List, Dict
from langchain_core.tools import tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import yaml
import os

# 🔧 YAML을 Document 리스트로 변환
def yaml_to_documents(yaml_path: str) -> List[Document]:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    docs = []
    for path, methods in data.get("paths", {}).items():
        for method, details in methods.items():
            summary = details.get("summary", "")
            responses = details.get("responses", {})
            parameters = details.get("parameters", [])

            inputs = [f"{p.get('name')}: {p.get('description', '')}" for p in parameters]
            outputs = [f"{code}: {r.get('description', '')}" for code, r in responses.items()]

            content = f"""### {method.upper()} {path}
설명: {summary}
입력:
{chr(10).join(inputs) or '없음'}

출력:
{chr(10).join(outputs) or '없음'}
"""
            docs.append(Document(page_content=content, metadata={"api_path": path}))
    return docs

# 🔧 리트리버 생성 함수
def create_yaml_retriever(yaml_path: str):
    documents = yaml_to_documents(yaml_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(split_docs, embeddings)

    return vectorstore.as_retriever(search_kwargs={"k": 5})

# ✅ LLM 툴 등록
@tool
def yaml_search(query: str, file_path: str) -> List[Dict[str, str]]:
    """
    Search the specified OpenAPI YAML file for information related to the input query.
    Useful for extracting API info such as inputs and outputs for a specific feature.
    """
    retriever = create_yaml_retriever(file_path)
    docs = retriever.invoke(query)

    return [{"content": doc.page_content, "source": doc.metadata.get("api_path", "unknown")} for doc in docs]

yaml_search.name = "yaml_search"
yaml_search.description = (
    "Search a specified OpenAPI YAML file for relevant API info related to a given feature. "
    "Requires the path to the YAML file and a query like '회원가입 API'."
)
