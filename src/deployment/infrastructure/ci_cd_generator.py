
from pathlib import Path

import yaml


class CICDGenerator:
    """
    Generates CI/CD pipelines. Currently supports GitHub Actions.
    """

    def generate_github_actions(self, output_path: Path, project_type: str = "fullstack"):
        """
        Create .github/workflows/deploy.yml
        """
        workflow_dir = output_path / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)

        workflow_content = {
            "name": "Production Deploy",
            "on": {
                "push": {"branches": ["main"]},
                "pull_request": {"branches": ["main"]}
            },
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v3"},
                        {"name": "Setup Node", "uses": "actions/setup-node@v3", "with": {"node-version": "18"}},
                        {"name": "Install Frontend", "run": "cd frontend && npm ci"},
                        {"name": "Lint Frontend", "run": "cd frontend && npm run lint"},
                        # Add Python steps if backend exists
                        {"name": "Setup Python", "uses": "actions/setup-python@v4", "with": {"python-version": "3.11"}},
                        {"name": "Install Backend", "run": "pip install -r backend/requirements.txt"},
                        {"name": "Test Backend", "run": "pytest backend/tests"}
                    ]
                },
                "deploy": {
                    "needs": "test",
                    "if": "github.ref == 'refs/heads/main'",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"name": "Deploy Info", "run": "echo 'Deploying to Vercel/Render...'"}
                        # Real steps would use Vercel/Render actions or CLI
                    ]
                }
            }
        }

        file_path = workflow_dir / "deploy.yml"
        with open(file_path, "w") as f:
            yaml.dump(workflow_content, f, sort_keys=False)

        return file_path
