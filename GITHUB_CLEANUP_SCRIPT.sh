#!/bin/bash

# GitHub에 업로드할 필요한 파일만 남기고 정리하는 스크립트

echo "=========================================="
echo "GitHub 폴더 정리 시작"
echo "=========================================="
echo ""

# 1. 필요한 파일 목록 (보관)
KEEP_FILES=(
  "GITHUB_README.md"
  "CONTRIBUTING.md"
  "CLAUDE.md"
  "requirements.txt"
  "package.json"
  "LICENSE"
  ".gitignore"
  ".env.example"
  ".github"
  "docs"
  "agents"
  "src"
  "tests"
  "examples"
  "backend"
  "frontend"
)

# 2. 불필요한 파일 삭제 (테스트/로그/분석 파일들)
REMOVE_FILES=(
  "ARCHITECTURE.md"
  "CODE_REVIEW_FIXES_APPLIED.md"
  "CRITICAL_FIXES_PHASE1.md"
  "DELIVERABLES_MANIFEST.md"
  "E2E_PROJECT_SIMULATION_EXPENSE_TRACKER.md"
  "EFFECTIVENESS_METRICS.md"
  "ENVIRONMENT_SETUP.md"
  "FAQ.md"
  "FINAL_INTEGRATION_TEST_REPORT.md"
  "FINAL_STATUS.md"
  "FINAL_SYSTEM_APPROVAL.md"
  "FIXES_VALIDATION_SUMMARY.txt"
  "GITHUB_DOCS_READY.md"
  "GITHUB_DOCS_SUMMARY.txt"
  "GITHUB_FILES_SUMMARY.txt"
  "GITHUB_PREPARATION_SUMMARY.md"
  "GITHUB_RELEASE_CHECKLIST.md"
  "GITHUB_STRUCTURE.md"
  "GITHUB_UPLOAD_GUIDE.md"
  "IMPLEMENTATION_COMPLETE.md"
  "IMPLEMENTATION_SUMMARY.md"
  "IMPROVEMENT_SUMMARY.md"
  "INTEGRATION_VALIDATION_CHECKLIST.md"
  "ISSUES_AND_IMPROVEMENTS.md"
  "MASTER_PROJECT_SUMMARY.md"
  "MASTER_STATUS_REPORT.md"
  "Main_Template_260303.html"
  "PERFORMANCE_BOTTLENECK_ANALYSIS.md"
  "PERFORMANCE_DELIVERABLES.txt"
  "PERFORMANCE_TESTING_INDEX.md"
  "PERFORMANCE_TESTING_SUMMARY.md"
  "PERFORMANCE_TEST_RESULTS.md"
  "PHASE1_CRITICAL_FIXES_SUMMARY.md"
  "PHASE1_INDEX.md"
  "PHASE2_COMPLETION_REPORT.md"
  "PHASE2_DELIVERABLES.txt"
  "PHASE2_HIGH_PRIORITY_FIXES.md"
  "PHASE2_IMPLEMENTATION_INDEX.md"
  "PHASE3_IMPLEMENTATION_SUMMARY.md"
  "PHASE3_INDEX.md"
  "PHASE3_QUALITY_OPTIMIZATIONS.md"
  "PHASE4_IMPLEMENTATION.md"
  "PHASE_1_SUMMARY.md"
  "PHASE_2_CHECKPOINT.md"
  "PHASE_3_CHECKPOINT.md"
  "PHASE_3_PLAN.md"
  "PHASE_4_SUMMARY.md"
  "PHASE_5_FINAL_SUMMARY.md"
  "PHASE_6_COMPLETION_SUMMARY.md"
  "PROJECT_VALIDATION_REPORT.md"
  "PRODUCTION_DEPLOYMENT_CHECKLIST.md"
  "PRODUCTION_READY_CHECKLIST.md"
  "QUICK_WINS_FINE_TUNING_PLAN.md"
  "QUICK_WINS_REVIEW.md"
  "QUICK_WINS_REVIEW_INDEX.md"
  "README_VALIDATION.md"
  "RELEASE_NOTES.md"
  "ROLLBACK_CHECKLIST.md"
  "ROI_ANALYSIS.md"
  "STATUS.md"
  "SYSTEM_ACTIVATION_GUIDE.md"
  "SYSTEM_VALIDATION_SUMMARY.md"
)

echo "삭제할 불필요한 파일들:"
for file in "${REMOVE_FILES[@]}"; do
  if [ -f "/workspace/$file" ]; then
    rm "/workspace/$file"
    echo "  ✓ $file"
  fi
done

echo ""
echo "=========================================="
echo "정리 완료!"
echo "=========================================="
echo ""
echo "보관된 파일/폴더:"
for item in "${KEEP_FILES[@]}"; do
  if [ -e "/workspace/$item" ]; then
    if [ -d "/workspace/$item" ]; then
      echo "  📁 $item/"
    else
      echo "  📄 $item"
    fi
  fi
done
