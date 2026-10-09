import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


SCRIPT = Path(__file__).with_name("portfolio.py")


class PortfolioTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "company" / "policies").mkdir(parents=True)
        (self.root / "inbox" / "open").mkdir(parents=True)
        (self.root / "projects" / "photo").mkdir(parents=True)
        self.dag = self.root / "projects" / "photo" / "dag.yaml"
        self.dag.write_text(yaml.safe_dump({"phases": [{"tasks": [
            {"id": "T-001", "title": "수신자 웹", "status": "done", "e2e": {"required": True, "covered_by": ["TC-1"]}},
            {"id": "T-002", "title": "업로더", "status": "committed", "depends_on": ["T-001"], "e2e": {"required": True, "covered_by": []}},
        ]}]}, allow_unicode=True), encoding="utf-8")
        self.context = self.root / "projects" / "photo" / "summary-context.yaml"
        self.context.write_text("""project: 포토
checked_at: 2026-09-28
goal: 사진 링크 공유
current_flows:
  - 격리 QA에서 수신자 웹 확인
next_release: 업로더 검증
blockers:
  - reason: 실 API 미검증
    clears_when: 브라우저 QA 통과
next_actions:
  - T-002 실 API QA 수행
user_approval:
  state: none
  reason: 로컬 QA이므로 사장 결재 불필요
discussion:
  state: none
evidence:
  - evidence.md
""", encoding="utf-8")
        (self.context.parent / "evidence.md").write_text("증거", encoding="utf-8")
        (self.root / "company" / "policies" / "hq-sweep.yaml").write_text(yaml.safe_dump({
            "projects": [{"id": "photo", "dag_path": "projects/photo/dag.yaml"},
                         {"id": "blog", "dag_path": None, "onboarding_task": "T-008"}]
        }), encoding="utf-8")
        self.blog_context = self.root / "projects" / "blog-context.yaml"
        self.blog_context.write_text("""project: 블로그
checked_at: 2026-09-28
next_actions:
  - T-008 첫 DAG 작성
user_approval:
  state: none
  reason: 등록 제품 온보딩
discussion:
  state: optional
  topic: 첫 출시 우선순위
evidence:
  - blog-evidence.md
""", encoding="utf-8")
        (self.root / "projects" / "blog-evidence.md").write_text("증거", encoding="utf-8")
        self.manifest = self.root / "company" / "development-status.yaml"
        self.manifest.write_text("""schema: 1
projects:
  photo: projects/photo/summary-context.yaml
  blog: projects/blog-context.yaml
separate_approvals:
  - id: HQ-T-015
    action: GCP 예산 알림 설정
    needs: [대상 프로젝트, 월 예산]
    blocks_development: false
    evidence: projects/photo/evidence.md
""", encoding="utf-8")

    def run_script(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root),
                               "--as-of", "2026-09-28"], text=True, capture_output=True)

    def test_fixed_project_and_approval_report(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("지금 필요한 사장 승인: 0건", result.stdout)
        self.assertIn("포토", result.stdout)
        self.assertIn("다음 작업: T-002 실 API QA 수행", result.stdout)
        self.assertIn("해제 조건: 브라우저 QA 통과", result.stdout)
        self.assertIn("사장 승인: 불필요 — 로컬 QA이므로 사장 결재 불필요", result.stdout)
        self.assertIn("블로그", result.stdout)
        self.assertIn("DAG 없음", result.stdout)
        self.assertIn("논의: 선택 — 첫 출시 우선순위", result.stdout)
        self.assertIn("별도 실행 전 승인: HQ-T-015", result.stdout)

    def test_new_open_decision_prevents_zero_approval_claim(self):
        (self.root / "inbox" / "open" / "decision.md").write_text("""---
id: INBOX-1
kind: decision
severity: blocking
title: 운영 배포 여부
product: photo
decision: null
---
본문
""", encoding="utf-8")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("지금 필요한 사장 승인: 1건", result.stdout)
        self.assertIn("INBOX-1 운영 배포 여부", result.stdout)
        self.assertIn("사장 승인: 필요 — INBOX-1 운영 배포 여부", result.stdout)

    def test_missing_approval_classification_fails_closed(self):
        text = self.context.read_text(encoding="utf-8")
        self.context.write_text(text.replace("user_approval:\n  state: none\n  reason: 로컬 QA이므로 사장 결재 불필요\n", ""), encoding="utf-8")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("지금 필요한 사장 승인: 0건", result.stdout)

    def test_stale_context_fails_closed(self):
        text = self.context.read_text(encoding="utf-8")
        self.context.write_text(text.replace("2026-09-28", "2026-09-01"), encoding="utf-8")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("지금 필요한 사장 승인: 0건", result.stdout)

    def test_stale_project_without_dag_fails_closed(self):
        text = self.blog_context.read_text(encoding="utf-8")
        self.blog_context.write_text(text.replace("2026-09-28", "2026-09-01"), encoding="utf-8")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("지금 필요한 사장 승인: 0건", result.stdout)

    def test_new_registered_project_requires_context(self):
        path = self.root / "company" / "policies" / "hq-sweep.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["projects"].append({"id": "letter", "dag_path": None})
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("프로젝트 목록이 다릅니다", result.stderr)


if __name__ == "__main__":
    unittest.main()
