import os

def scan_source_files(base_path: str, keywords: list[str], extensions={".ts", ".html", ".js", ".php", ".py"}) -> dict:
    results = {}
    normalized_keywords = [kw.lower().strip() for kw in keywords if kw.strip()]

    for root, _, files in os.walk(base_path):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except Exception as e:
                    continue  # 파일 열기 실패 시 무시

                matched_lines = []
                for idx, line in enumerate(lines):
                    line_lc = line.lower()
                    if any(kw in line_lc for kw in normalized_keywords):
                        matched_lines.append((idx + 1, line.strip()))

                if matched_lines:
                    results[full_path] = matched_lines

    return results
