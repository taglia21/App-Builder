"""Export pipeline results to various formats."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class ResultsExporter:
    """Exports pipeline results to organized files."""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.timestamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def export_pain_points(self, pain_points: List[Any]) -> str:
        """Export pain points to JSON and CSV."""
        # JSON export
        json_path = self.run_dir / "pain_points.json"
        data = []
        for pp in pain_points:
            if hasattr(pp, '__dict__'):
                data.append({k: str(v) for k, v in pp.__dict__.items()})
            elif hasattr(pp, 'model_dump'):
                data.append(pp.model_dump())
            else:
                data.append(str(pp))

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        # CSV export
        csv_path = self.run_dir / "pain_points.csv"
        if data:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        return str(json_path)

    def export_ideas(self, ideas: List[Any], evaluations: List[Any] = None) -> str:
        """Export ideas with scores to JSON and CSV."""
        # Create lookup for scores
        scores = {}
        if evaluations:
            for ev in evaluations:
                idea_id = ev.idea_id if hasattr(ev, 'idea_id') else ev.get('idea_id')
                score = ev.total_score if hasattr(ev, 'total_score') else ev.get('total_score', 0)
                scores[idea_id] = score

        # JSON export
        json_path = self.run_dir / "ideas.json"
        data = []
        for idea in ideas:
            if hasattr(idea, 'model_dump'):
                item = idea.model_dump()
            elif hasattr(idea, '__dict__'):
                item = {k: str(v) for k, v in idea.__dict__.items()}
            else:
                item = {'data': str(idea)}

            idea_id = item.get('id', '')
            item['score'] = scores.get(idea_id, 0)
            data.append(item)

        # Sort by score
        data.sort(key=lambda x: x.get('score', 0), reverse=True)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        # CSV export
        csv_path = self.run_dir / "ideas.csv"
        if data:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        # Markdown summary
        md_path = self.run_dir / "ideas_summary.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Generated Startup Ideas\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"Total Ideas: {len(data)}\n\n")
            f.write("---\n\n")

            for i, idea in enumerate(data[:10], 1):
                f.write(f"## {i}. {idea.get('name', 'Unnamed')}\n\n")
                f.write(f"**Score:** {idea.get('score', 'N/A')}/100\n\n")
                f.write(f"**Problem:** {idea.get('problem_statement', 'N/A')[:200]}\n\n")
                f.write(f"**Solution:** {idea.get('solution_description', 'N/A')[:200]}\n\n")
                f.write(f"**Revenue Model:** {idea.get('revenue_model', 'N/A')}\n\n")
                f.write("---\n\n")

        return str(json_path)

    def export_winning_idea(self, idea: Any, evaluation: Any = None) -> str:
        """Export detailed winning idea."""
        json_path = self.run_dir / "winning_idea.json"

        if hasattr(idea, 'model_dump'):
            data = idea.model_dump()
        elif hasattr(idea, '__dict__'):
            data = {k: str(v) for k, v in idea.__dict__.items()}
        else:
            data = {'data': str(idea)}

        if evaluation:
            if hasattr(evaluation, 'model_dump'):
                data['evaluation'] = evaluation.model_dump()
            elif hasattr(evaluation, '__dict__'):
                data['evaluation'] = {k: str(v) for k, v in evaluation.__dict__.items()}

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        return str(json_path)

    def export_run_summary(self, stats: Dict[str, Any]) -> str:
        """Export run statistics."""
        json_path = self.run_dir / "run_summary.json"

        stats['timestamp'] = self.timestamp
        stats['output_directory'] = str(self.run_dir)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, default=str)

        # Also create a readable summary
        md_path = self.run_dir / "README.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Pipeline Run Summary\n\n")
            f.write(f"**Timestamp:** {self.timestamp}\n\n")
            f.write("## Statistics\n\n")
            for key, value in stats.items():
                f.write(f"- **{key}:** {value}\n")
            f.write("\n## Files Generated\n\n")
            for file in self.run_dir.glob("*"):
                f.write(f"- `{file.name}`\n")

        return str(self.run_dir)

    def get_output_dir(self) -> str:
        return str(self.run_dir)
