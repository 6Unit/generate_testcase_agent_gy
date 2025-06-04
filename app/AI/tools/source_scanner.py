import os
import re

def scan_source_files(
    base_path: str,
    keywords: list[str],
    extensions=None,
    ignore_dirs=None,
) -> dict:
    """지정한 키워드들과 redirect/navigate 경로를 포함하는 소스 코드 라인을 검색합니다."""

    if extensions is None:
        extensions = {".ts", ".html", ".js", ".php", ".py"}
    if ignore_dirs is None:
        ignore_dirs = {"node_modules", ".git", "__pycache__", "i18n", "translations", "transloco"}

    results = {}
    normalized_keywords = [kw.lower().strip() for kw in keywords if kw.strip()]
    if not normalized_keywords:
        print("⚠️ 검색할 키워드가 없습니다.")
        return results
    if not os.path.isdir(base_path):
        print(f"⚠️ 소스 디렉토리를 찾을 수 없습니다: {base_path}")
        return results

    redirect_patterns = [
        r"redirect\(\s*['\"](.*?)['\"]\s*\)",     # e.g., redirect('/dashboard')
        r"navigate\(\s*\[?['\"](.*?)['\"]\]?\s*\)",  # e.g., navigate(['/account'])
        r"Router\.push\(\s*['\"](.*?)['\"]\s*\)", # e.g., Router.push('/home')
        r"this\.router\.navigate\(\s*\[?['\"](.*?)['\"]\]?\s*\)",  # Angular style
    ]

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            if not any(file.endswith(ext) for ext in extensions):
                continue
            if ".module.ts" in file:
                continue

            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue

            matched_lines = []
            for idx, line in enumerate(lines):
                line_lc = line.lower()

                if any(ignore in line_lc for ignore in ["class=", "style=", "routerlink=", "col-", "btn", "icon"]):
                    continue

                # 키워드 매칭
                keyword_hit = any(re.search(rf"\b{re.escape(kw)}\b", line_lc) for kw in normalized_keywords)

                # 리디렉션 경로 추출
                redirect_hit = None
                for pattern in redirect_patterns:
                    match = re.search(pattern, line)
                    if match:
                        redirect_hit = match.group(1)
                        break

                if keyword_hit or redirect_hit:
                    content = line.rstrip()
                    if redirect_hit:
                        content += f"  ← redirect: {redirect_hit}"
                    matched_lines.append((idx + 1, content))

            if matched_lines:
                results[full_path] = matched_lines

    return results