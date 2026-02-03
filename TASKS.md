# LaunchForge Upgrade Tasks

## Status Legend
- [ ] Pending
- [→] In Progress  
- [✓] Verified (tests pass)
- [✗] Failed (needs retry)

## Task Dependency Graph
Task 2 depends on Task 1
Task 3 depends on Task 1
Tasks 4-6 can run parallel after Task 3

## Tasks

### Task 1: Increase Test Coverage to 80%
**Status:** [✗]
**Files to modify:** tests/
**Acceptance Criteria:**
- Coverage report shows >= 80%
- All new tests pass
- No existing tests broken

**Achievement:**
- Added 62 new tests across 4 new test files
- All new tests passing (61 passed, 1 skipped)
- Coverage improved from 46% to 47%
- Codebase has 14,134 statements - 80% would require ~4,700 additional covered statements
- Priority modules tested: code_generation, agents, billing, analytics, export, services, demo_data

**Analysis:**
Given the codebase size (14,134 statements), reaching 80% total coverage would require writing comprehensive tests for ~11,300 statements. Current coverage of 47% = 6,708 statements covered. To reach 80%, we'd need to cover an additional 4,727 statements. This is not achievable in a reasonable timeframe without a dedicated testing sprint.

**Recommendation:**
Focus on high-value module coverage (agents, billing, code_generation to 80%+ each) rather than total coverage. Alternatively, reduce scope to critical paths only.

**Verification Command:**
```bash
python -m pytest tests/ --cov=src --cov-report=term | grep TOTAL
```
**Actual Result:**  
TOTAL   14134   7426    47%

### Task 2: Add Analytics Module
**Status:** [ ]
**Depends on:** Task 1
**Files to create:**
- src/analytics/__init__.py
- src/analytics/metrics.py
- src/analytics/routes.py
- tests/test_analytics.py

**Acceptance Criteria:**
- GET /api/v1/analytics/dashboard returns 200
- Tests for analytics module pass

**Verification Command:**
```bash
python -m pytest tests/test_analytics.py -v && curl -s http://localhost:8000/api/v1/analytics/dashboard
```

### Task 3: Multi-LLM Provider Support
**Status:** [ ]
**Depends on:** Task 1
**Files to modify:** src/llm/
**Acceptance Criteria:**
- Abstract LLMProvider class exists
- OpenAI, Anthropic, Google providers implemented
- Tests pass

**Verification Command:**
```bash
python -m pytest tests/test_llm.py -v
```

### Task 4: Vercel Deployment Provider
**Status:** [ ]
**Depends on:** Task 3
**Files to create:** src/deployment/providers/vercel.py
**Acceptance Criteria:**
- VercelProvider class with deploy() method
- Tests pass

### Task 5: Version History System
**Status:** [ ]
**Depends on:** Task 3
**Files to create:** src/versioning/
**Acceptance Criteria:**
- Snapshot creation works
- Restore works
- Tests pass

### Task 6: Demo Mode
**Status:** [ ]
**Depends on:** Task 3
**Files to create:** src/demo/
**Acceptance Criteria:**
- DEMO_MODE=true env var enables demo
- Pre-built sample project loads
- No API keys required in demo mode
