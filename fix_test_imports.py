# Fix the test_agents.py imports properly
with open('tests/agents/test_agents.py', 'r') as f:
    lines = f.readlines()

# Find where the bad import structure is and fix it
fixed_content = '''from dataclasses import dataclass
import pytest

from src.agents.messages import (
    AgentRole, CriticDecision, TaskStatus, ExecutionPlan,
    GeneratedCode, CriticReview, OrchestrationState
)

from src.agents.critics.code_critic import CodeCritic
'''

# Find where class TestMessages starts and keep everything from there
for i, line in enumerate(lines):
    if 'class TestMessages' in line:
        fixed_content += ''.join(lines[i:])
        break

with open('tests/agents/test_agents.py', 'w') as f:
    f.write(fixed_content)

print('Fixed test_agents.py imports')
