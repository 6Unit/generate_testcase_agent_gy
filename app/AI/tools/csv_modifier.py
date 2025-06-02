# tools/csv_modifier.py

import pandas as pd

def apply_corrections_to_csv(csv_path: str, corrections: list[dict], output_path: str = None):
    df = pd.read_csv(csv_path)

    for c in corrections:
        if not c.get("correction_required"):
            continue

        row_index = df[df["No."] == c["No"]].index
        if not row_index.empty:
            df.at[row_index[0], c["field"]] = c["actual"]

    save_path = output_path or csv_path
    df.to_csv(save_path, index=False, encoding="utf-8-sig")
    print(f"✅ 테스트케이스 CSV가 수정되었습니다 → {save_path}")
