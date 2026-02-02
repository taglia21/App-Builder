# Organizational Intelligence Framework

Implementation of the multi-agent governance model based on the paper:
**"If You Want Coherence, Orchestrate a Team of Rival Multi-Agent Models of Organizational Intelligence"**

## Overview

This framework transforms the App-Builder from a single-agent system into a **multi-agent organization** with checks and balances, achieving higher quality outputs through **constructive rivalry** between agents with different perspectives.

## Architecture: Separation of Powers

The framework implements three branches of governance, inspired by democratic systems:

### 1. Legislative Branch (Planning & Debate)
**Location**: `src/agents/governance/legislative.py`

**Responsibility**: Propose and debate strategies through rival planners

**Rival Planners**:
- **Conservative Planner** (`planners/conservative_planner.py`)
  - Philosophy: Risk-averse, proven patterns
  - Strengths: Stability, extensive testing, defensive programming
  - Use case: Mission-critical systems, regulated industries

- **Innovative Planner** (`planners/innovative_planner.py`)
  - Philosophy: Cutting-edge, modern approaches
  - Strengths: Scalability, clean architecture, future-proofing
  - Use case: Startups, greenfield projects, competitive advantage

- **Pragmatic Planner** (`planners/pragmatic_planner.py`)
  - Philosophy: Balanced, outcome-focused
  - Strengths: Right tool for job, clear trade-offs, MVP focus
  - Use case: Most real-world projects with time/budget constraints

**Process**:
1. All three planners propose strategies concurrently
2. Plans are compared and debated
3. `PlanSynthesizer` merges the best ideas from each approach
4. Synthesized plan submitted to Judicial for review

### 2. Judicial Branch (Review & Veto Authority)
**Location**: `src/agents/governance/judicial.py`

**Responsibility**: Review code quality through rival critics with veto power

**Rival Critics** (all run in parallel):
- **Code Critic** (`critics/code_critic.py`)
  - Focus: Syntax, logic, code quality
  - Veto authority: Yes (critical for basic correctness)

- **Security Critic** (`critics/security_critic.py`)
  - Focus: SQL injection, XSS, hardcoded secrets, command injection
  - Veto authority: Yes (critical for security)
  - Static analysis + LLM deep analysis

- **Performance Critic** (`critics/performance_critic.py`)
  - Focus: N+1 queries, nested loops, async issues, pagination
  - Veto authority: No (can recommend changes)

- **UX Critic** (`critics/ux_critic.py`)
  - Focus: Loading states, error handling, accessibility, form validation
  - Veto authority: No (can recommend changes)

- **Output Critic** (`critics/output_critic.py`)
  - Focus: Requirements matching, output validation
  - Veto authority: No (can recommend changes)

**Decision Logic**:
- **REJECT**: Any critic with veto authority rejects, or 2+ critics reject
- **NEEDS_REVISION**: Majority of critics request changes
- **CONDITIONAL_APPROVAL**: Approved with noted concerns from minority
- **APPROVED**: Majority approve, consensus score ≥ 60%

### 3. Executive Branch (Controlled Execution)
**Location**: `src/agents/governance/executive.py`

**Responsibility**: Execute approved plans with oversight

**Powers**:
- Execute code generation through approved plans only
- Request real-time veto checks from Judicial before critical steps
- Manage execution state and error handling
- Report progress transparently to all branches

**Limitations**:
- Cannot execute without Legislative approval
- Cannot override Judicial vetoes
- Cannot modify plans during execution

## Governance Orchestrator

**Location**: `src/agents/governance_orchestrator.py`

**Main Entry Point**: `GovernanceOrchestrator.generate_app()`

**Execution Flow**:

```
1. LEGISLATIVE PHASE
   ├─ Conservative Planner proposes
   ├─ Innovative Planner proposes  
   ├─ Pragmatic Planner proposes
   ├─ Plans debated and compared
   └─ PlanSynthesizer creates optimal plan

2. EXECUTIVE PHASE  
   ├─ Execute synthesized plan
   ├─ Generate code through CodeWriter
   └─ Check for vetoes at each step

3. JUDICIAL PHASE
   ├─ Code Critic reviews
   ├─ Security Critic reviews (parallel)
   ├─ Performance Critic reviews (parallel)
   ├─ UX Critic reviews (parallel)
   ├─ Output Critic reviews (parallel)
   └─ Consensus decision made

4. ITERATION (if needed)
   ├─ If REJECTED/NEEDS_REVISION:
   │   ├─ Feedback incorporated
   │   └─ Return to step 1 with updated requirements
   └─ If APPROVED:
       └─ Return final code with governance metadata
```

## Usage

### Basic Usage

```python
from src.agents import GovernanceOrchestrator, LLMProvider

# Initialize
llm = LLMProvider(...)
orchestrator = GovernanceOrchestrator(llm)

# Generate app with full governance
result = await orchestrator.generate_app(
    requirements="Build a REST API for user management",
    context={"tech_stack": "FastAPI"}
)

# Access governance metadata
print(f"Planners consulted: {result.metadata['governance']['planners_consulted']}")
print(f"Critics consulted: {result.metadata['governance']['critics_consulted']}")
print(f"Consensus score: {result.metadata['governance']['consensus_score']}")
```

### Get Governance Statistics

```python
stats = orchestrator.get_stats()
print(f"Plans proposed: {stats['plans_proposed']}")
print(f"Reviews conducted: {stats['reviews_conducted']}")
print(f"Vetoes issued: {stats['vetoes_issued']}")
```

### Access Debate Logs

```python
# Get legislative debate log
debate_log = await orchestrator.get_debate_log(session_id)
for entry in debate_log:
    print(f"{entry['planner_1']} vs {entry['planner_2']}")
    print(f"Agreement score: {entry['agreement_score']}")

# Get judicial review details
review = await orchestrator.get_review_details(review_id)
for critic_review in review['critic_reviews']:
    print(f"{critic_review['specialty']}: {critic_review['decision']}")
```

## Key Benefits

### 1. Higher Quality Through Rivalry
- **Multiple Perspectives**: Different planners catch different issues
- **No Blind Spots**: Security critic focuses on vulnerabilities while Performance critic focuses on efficiency
- **Self-Correction**: Agents catch each other's mistakes

### 2. Emergent Coherence
- **Synthesis Over Single View**: Best ideas from all planners merged
- **Consensus Building**: Critics must reach agreement
- **Balanced Decisions**: Trade-offs explicitly considered

### 3. Transparency & Accountability
- **Audit Trails**: Full logs of who proposed what and why
- **Veto Reasons**: Clear explanations when code is rejected
- **Debate Logs**: See how rival planners disagreed and compromised

### 4. Adaptability
- **Context-Aware**: Conservative for critical systems, innovative for startups
- **Iterative Refinement**: Feedback loops improve quality
- **Learning**: Patterns in debate logs inform future decisions

## Comparison: Before vs After

| Aspect | Single-Agent (Before) | Organizational Intelligence (After) |
|--------|----------------------|------------------------------------|
| Planning | One planner's view | 3 rival planners + synthesis |
| Validation | Sequential critics | 5 parallel critics with specialties |
| Error Detection | Hope one agent catches it | Multiple agents with different focuses |
| Quality Assurance | Post-hoc validation | Continuous checks and balances |
| Decision Making | Single perspective | Consensus with dissent tracked |
| Accountability | Black box | Full audit trail |
| Veto Authority | Manual review | Automated with clear criteria |

## Configuration

### Adjust Veto Authority

Edit `judicial.py` to change which critics have veto power:

```python
has_veto = any(
    r.decision == CriticDecision.REJECT 
    for r in reviews 
    if r.specialty in ["security", "code", "performance"]  # Add/remove specialties
)
```

### Adjust Consensus Threshold

```python
if majority_decision == CriticDecision.APPROVE and consensus_score >= 0.7:  # Change from 0.6
    final_decision = ReviewDecision.APPROVED
```

### Add More Planners

1. Create new planner class in `src/agents/planners/`
2. Add to Legislative Branch initialization:
   ```python
   self.your_planner = YourPlanner(llm_provider)
   ```
3. Add to `_gather_proposals()` task list

### Add More Critics

1. Create new critic class in `src/agents/critics/`
2. Add to Judicial Branch initialization:
   ```python
   self.critics["your_specialty"] = YourCritic(llm_provider)
   ```
3. Update `__init__.py` to export

## Testing

Run integration tests:

```bash
pytest tests/agents/test_governance_integration.py -v
```

## Performance Considerations

- **Parallel Execution**: Planners and critics run concurrently
- **Caching**: Plan synthesis results cached within session
- **Early Termination**: Critical failures stop execution immediately
- **Iteration Limit**: Max 3 iterations prevents infinite loops

## Future Enhancements

1. **Machine Learning**: Learn from past debates to improve synthesis
2. **Dynamic Weights**: Adjust planner influence based on context
3. **Specialized Critics**: Add domain-specific critics (compliance, legal, etc.)
4. **Interactive Mode**: Allow human input in Legislative debates
5. **Metrics Dashboard**: Visualize governance patterns and trends

## References

- Paper: "If You Want Coherence, Orchestrate a Team of Rival Multi-Agent Models of Organizational Intelligence"
- Implementation Date: February 2026
- Framework Version: 1.0

---

**Maintained by**: App-Builder Team  
**Last Updated**: February 2, 2026
