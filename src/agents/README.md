# Multi-Agent Organizational Intelligence System

This module implements a multi-agent system based on the paper "If You Want Coherence, Orchestrate a Team of Rival Multi-Agent Models of Organizational Intelligence".

## Architecture

The system consists of four specialized agents coordinated by an orchestrator:

### Agents

1. **TaskPlannerAgent** (`planners/planner_agent.py`)
   - Decomposes high-level requirements into actionable tasks
   - Pre-declares acceptance criteria before planning
   - Generates structured task plans with dependencies

2. **CodeWriterAgent** (`writers/code_writer.py`)
   - Generates code based on task specifications
   - Follows best practices and coding standards
   - Produces documented, tested code

3. **CodeCriticAgent** (`critics/code_critic.py`)
   - Reviews generated code for quality issues
   - Has **veto authority** to reject substandard code
   - Provides actionable feedback for improvements

4. **OutputCriticAgent** (`critics/output_critic.py`)
   - Validates final outputs against requirements
   - Ensures coherence and completeness
   - Final quality gate before delivery

### Orchestrator

The `AIOfficeOrchestrator` (`orchestrator.py`) coordinates the agents:
- Manages the workflow between agents
- Handles iterative improvement loops
- Implements checkpointing for state recovery
- Enforces critic veto decisions

## Key Features

- **Pre-declared Acceptance Criteria**: Each agent declares success criteria before execution
- **Veto Authority**: Critics can reject work at any stage
- **Iterative Improvement**: Agents can loop back with feedback
- **Checkpointing**: State persistence for recovery
- **Pydantic-validated Messages**: Structured communication between agents

## API Endpoints

The multi-agent system exposes the following endpoints at `/api/v2`:

- `GET /api/v2/health` - Health check for the multi-agent system
- `GET /api/v2/info` - System information and capabilities
- `POST /api/v2/generate` - Generate an application using the multi-agent system

## Usage

### Environment Variables

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Starting the Server

```bash
python run_server.py
```

### Example API Request

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v2/generate",
    json={
        "name": "my-app",
        "description": "A todo list application",
        "requirements": [
            "User authentication",
            "CRUD operations for tasks",
            "Due date reminders"
        ]
    }
)
```

## File Structure

```
src/agents/
├── __init__.py
├── README.md           # This file
├── api_integration.py  # FastAPI integration and service layer
├── base.py             # Base agent class and LLM provider
├── messages.py         # Pydantic message types
├── orchestrator.py     # Agent coordination
├── routes.py           # API route definitions
├── critics/
│   ├── __init__.py
│   ├── code_critic.py
│   └── output_critic.py
├── planners/
│   ├── __init__.py
│   └── planner_agent.py
└── writers/
    ├── __init__.py
    └── code_writer.py
```

## Testing

Run the unit tests:

```bash
pytest tests/agents/test_agents.py -v
```

## References

- Paper: "If You Want Coherence, Orchestrate a Team of Rival Multi-Agent Models of Organizational Intelligence"
