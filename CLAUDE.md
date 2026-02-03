# Claude Development Guidelines for LaunchForge

## Priority Hierarchy (when rules conflict)
1. **Tests pass**: `pytest tests/ -v` must succeed
2. **Types valid**: `mypy src/ --strict` with zero errors
3. **No warnings**: Zero pytest warnings in output
4. **Backwards compatible**: Existing APIs unchanged
5. **Clean code**: Readable, maintainable, idiomatic Python

## Workflow
1. **Read first**: Examine relevant files before proposing changes. State: "Don't write yet"
2. **Propose**: Present changes in `<plan>` tags with reasoning
3. **Wait**: Require explicit "proceed" before implementation
4. **Implement incrementally**: One file at a time
5. **Verify**: After each file, run tests and report results using `<verification>` tags

## Required Patterns
- **Pydantic validation**: All messages/models inherit from `BaseModel` with strict typing
- **UTC timestamps**: Always use `datetime.now(timezone.utc)`, never `datetime.now()`
- **Type hints**: Annotate every function signature and class attribute
- **Structured logging**: Use `logger.info/warning/error` with contextual details
- **Result types**: Return typed results (e.g., `OrchestrationState`, `CriticReview`)
- **No TODOs**: Resolve or document uncertainties inline, never commit TODO comments

## Multi-Agent Architecture
- **Planners** → **Executors** (writers) → **Critics** (veto authority)
- Pre-declare `acceptance_criteria` in `ExecutionPlan` before execution
- Critics use `CriticDecision` enum: APPROVE | REJECT | REQUEST_CHANGES
- Veto authority: Critics can block with reasoning in `veto_reason`
- Retry logic: max_retries with feedback compilation

## When Stuck Protocol
After 2 failed attempts, respond with:
```
BLOCKED: [specific technical issue]
OPTIONS:
1. [Alternative approach A]
2. [Alternative approach B]
3. [Proposed workaround]
```

## Output Format
Use `<file>`, `<verification>`, `<reasoning>` tags to structure responses. Keep explanations concise, code idiomatic.
