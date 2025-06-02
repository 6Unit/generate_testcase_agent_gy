import os
import pandas as pd

class TestCaseCorrectionAgent:
    display_name = "테스트케이스 수정 에이전트"
    description = "검증 결과를 기반으로 테스트케이스 CSV의 잘못된 항목을 자동 수정하거나 삭제합니다."
    category = "테스트케이스 수정"
    features = "- 전체 필드 자동 교체\n- 삭제 후보 제거\n- 원본 또는 새 파일로 저장 가능"

    def __init__(self, case_csv_path: str, output_csv_path: str = None):
        self.case_csv_path = case_csv_path
        self.output_csv_path = output_csv_path or case_csv_path

    def run(self, validation_results: list[dict]):
        df = pd.read_csv(self.case_csv_path)
        df = df.fillna("")

        for result in validation_results:
            tc_no = result["No"]
            correction_required = result.get("correction_required", False)
            deletion_candidate = result.get("deletion_candidate", False)

            if deletion_candidate:
                df = df[df["No."] != tc_no]
                print(f"🗑️ TC {tc_no} 삭제됨")
            elif correction_required:
                revised = result["final_testcase"]
                for field, new_value in revised.items():
                    if field in df.columns:
                        df.loc[df["No."] == tc_no, field] = new_value
                        print(f"✏️ TC {tc_no} 수정됨 → {field} = \"{new_value}\"")

        df.to_csv(self.output_csv_path, index=False, encoding="utf-8-sig")
        print(f"\n📁 수정된 CSV 저장 완료: {self.output_csv_path}")
        return f"{len(validation_results)}건의 검증 결과를 반영하여 CSV 수정 완료"
