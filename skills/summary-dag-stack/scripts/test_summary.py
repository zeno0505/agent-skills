import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


SCRIPT = Path(__file__).with_name("summary.py")


class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dag = self.root / "dag.yaml"
        self.dag.write_text(yaml.safe_dump({"phases": [{"tasks": [
            {"id": "T-001", "title": "기반", "status": "done"},
            {"id": "T-002", "title": "화면", "status": "committed", "depends_on": ["T-001"]},
            {"id": "T-003", "title": "공개", "status": "pending", "depends_on": ["T-002"]},
            {"id": "T-004", "title": "나중에", "status": "deferred"},
        ]}]}, allow_unicode=True), encoding="utf-8")

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.dag), *args],
                              text=True, capture_output=True)

    def test_yaml_preserves_existing_summary_fields(self):
        result = self.run_script("--yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = yaml.safe_load(result.stdout)
        self.assertEqual(data["tasks"], 4)
        self.assertEqual(data["status_counts"],
                         {"done": 1, "committed": 1, "pending": 1, "deferred": 1})
        self.assertEqual(data["open"], 3)
        self.assertEqual(data["ready_count"], 2)
        self.assertEqual(data["waiting_count"], 1)
        self.assertEqual([item["id"] for item in data["ready"]], ["T-002", "T-004"])
        self.assertEqual(data["chokepoints"][0]["id"], "T-002")

    def test_text_separates_dependency_from_action_and_marks_missing_context(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("확인 시각 미기재", result.stdout)
        self.assertIn("목표: 확인 필요", result.stdout)
        self.assertIn("현재 사용 가능한 흐름: 확인 필요", result.stdout)
        self.assertIn("다음 공개 기준: 확인 필요", result.stdout)
        self.assertIn("의존성 길목: T-002", result.stdout)
        self.assertNotIn("착수 가능: T-004", result.stdout)

    def test_text_uses_verified_context_with_fixed_sections(self):
        context = self.root / "context.yaml"
        context.write_text("""project: 예시 제품
checked_at: 2026-09-28
goal: 사진 링크 공유
current_flows:
  - 받은 링크에서 사진 선택
next_release: 업로더에서 링크 생성 후 실제 API 검증
blockers:
  - reason: 실 API 검증 미완료
    clears_when: 격리 DB 브라우저 QA 통과
evidence:
  - docs/status.md
""", encoding="utf-8")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "status.md").write_text("검증 기록", encoding="utf-8")
        result = self.run_script("--context", str(context), "--as-of", "2026-09-28")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("예시 제품 — 2026-09-28 확인", result.stdout)
        self.assertIn("목표: 사진 링크 공유", result.stdout)
        self.assertIn("현재 사용 가능한 흐름: 받은 링크에서 사진 선택", result.stdout)
        self.assertIn("해제 조건: 격리 DB 브라우저 QA 통과", result.stdout)
        self.assertIn("근거: docs/status.md", result.stdout)

    def test_bad_context_does_not_silently_drop_blockers(self):
        context = self.root / "context.yaml"
        context.write_text("blockers:\n  - 설명만 있는 문자열\n", encoding="utf-8")
        result = self.run_script("--context", str(context))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("blockers", result.stderr)

    def test_timestamp_checked_at_reports_input_error_without_traceback(self):
        context = self.root / "context.yaml"
        context.write_text("""checked_at: 2026-09-28T12:00:00
goal: 사진 링크 공유
evidence:
  - status.md
""", encoding="utf-8")
        (self.root / "status.md").write_text("검증 기록", encoding="utf-8")
        result = self.run_script("--context", str(context), "--as-of", "2026-09-28")
        self.assertEqual(result.returncode, 1)
        self.assertIn("context.checked_at은 YYYY-MM-DD 날짜여야 합니다", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_e2e_is_visible(self):
        dag = yaml.safe_load(self.dag.read_text(encoding="utf-8"))
        dag["phases"][0]["tasks"][0]["e2e"] = {"required": True, "covered_by": "TC-1"}
        self.dag.write_text(yaml.safe_dump(dag, allow_unicode=True), encoding="utf-8")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("형식 오류 1건", result.stdout)


if __name__ == "__main__":
    unittest.main()
