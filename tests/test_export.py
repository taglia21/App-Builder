"""Tests for src/export/exporter.py - Results Export functionality."""
import json
import tempfile
from pathlib import Path

import pytest

from src.export.exporter import ResultsExporter


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def exporter(temp_output_dir):
    """Create a ResultsExporter instance."""
    return ResultsExporter(output_dir=temp_output_dir)


def test_exporter_initialization(exporter, temp_output_dir):
    """Test ResultsExporter initializes correctly."""
    assert exporter.output_dir == Path(temp_output_dir)
    assert exporter.run_dir.exists()
    assert str(exporter.run_dir).startswith(str(exporter.output_dir / "run_"))


def test_export_pain_points_empty(exporter):
    """Test exporting empty pain points list."""
    result = exporter.export_pain_points([])

    json_path = Path(result)
    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)
    assert data == []


def test_export_pain_points_with_dict(exporter):
    """Test exporting pain points from dict-like objects."""
    class MockPainPoint:
        def __init__(self, problem, severity):
            self.problem = problem
            self.severity = severity

    pain_points = [
        MockPainPoint("Slow loading", "high"),
        MockPainPoint("Poor UX", "medium")
    ]

    result = exporter.export_pain_points(pain_points)

    json_path = Path(result)
    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)

    assert len(data) == 2
    assert data[0]['problem'] == "Slow loading"
    assert data[1]['severity'] == "medium"

    # Check CSV was also created
    csv_path = exporter.run_dir / "pain_points.csv"
    assert csv_path.exists()


def test_export_pain_points_with_pydantic_model(exporter):
    """Test exporting pain points from Pydantic models."""
    from pydantic import BaseModel

    class PainPoint(BaseModel):
        problem: str
        severity: str

    pain_points = [
        PainPoint(problem="Issue 1", severity="high"),
        PainPoint(problem="Issue 2", severity="low")
    ]

    result = exporter.export_pain_points(pain_points)

    json_path = Path(result)
    with open(json_path) as f:
        data = json.load(f)

    assert len(data) == 2
    assert data[0]['problem'] == "Issue 1"


def test_export_ideas_without_evaluations(exporter):
    """Test exporting ideas without evaluation scores."""
    class MockIdea:
        def model_dump(self):
            return {
                'id': 'idea1',
                'name': 'Test Idea',
                'problem_statement': 'Problem',
                'solution_description': 'Solution'
            }

    ideas = [MockIdea()]
    result = exporter.export_ideas(ideas)

    json_path = Path(result)
    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)

    assert len(data) == 1
    assert data[0]['name'] == 'Test Idea'
    assert data[0]['score'] == 0

    # Check CSV and markdown created
    assert (exporter.run_dir / "ideas.csv").exists()
    assert (exporter.run_dir / "ideas_summary.md").exists()


def test_export_ideas_with_evaluations(exporter):
    """Test exporting ideas with evaluation scores."""
    class MockIdea:
        def model_dump(self):
            return {
                'id': 'idea1',
                'name': 'Great Idea',
                'problem_statement': 'Problem text',
                'solution_description': 'Solution text',
                'revenue_model': 'Subscription'
            }

    class MockEvaluation:
        def __init__(self, idea_id, total_score):
            self.idea_id = idea_id
            self.total_score = total_score

    ideas = [MockIdea()]
    evaluations = [MockEvaluation('idea1', 85.5)]

    result = exporter.export_ideas(ideas, evaluations)

    json_path = Path(result)
    with open(json_path) as f:
        data = json.load(f)

    assert data[0]['score'] == 85.5


def test_export_ideas_sorted_by_score(exporter):
    """Test ideas are sorted by score in descending order."""
    ideas = [
        {'id': 'idea1', 'name': 'Low Score'},
        {'id': 'idea2', 'name': 'High Score'},
        {'id': 'idea3', 'name': 'Medium Score'}
    ]

    class MockEval:
        def __init__(self, idea_id, score):
            self.idea_id = idea_id
            self.total_score = score

    evaluations = [
        MockEval('idea1', 30),
        MockEval('idea2', 90),
        MockEval('idea3', 60)
    ]

    # Convert dicts to objects with model_dump
    class IdeaObj:
        def __init__(self, data):
            self.data = data
        def model_dump(self):
            return self.data

    idea_objects = [IdeaObj(i) for i in ideas]

    result = exporter.export_ideas(idea_objects, evaluations)

    json_path = Path(result)
    with open(json_path) as f:
        data = json.load(f)

    assert data[0]['score'] == 90  # Highest first
    assert data[1]['score'] == 60
    assert data[2]['score'] == 30


def test_export_ideas_markdown_summary(exporter):
    """Test markdown summary generation."""
    class MockIdea:
        def model_dump(self):
            return {
                'id': 'idea1',
                'name': 'Amazing Startup',
                'problem_statement': 'Big problem here',
                'solution_description': 'Great solution',
                'revenue_model': 'SaaS'
            }

    exporter.export_ideas([MockIdea()])

    md_path = exporter.run_dir / "ideas_summary.md"
    assert md_path.exists()

    content = md_path.read_text()
    assert "# Generated Startup Ideas" in content
    assert "Amazing Startup" in content
    assert "Score:" in content


def test_export_winning_idea(exporter):
    """Test exporting winning idea."""
    class MockIdea:
        def model_dump(self):
            return {
                'id': 'winner',
                'name': 'Best Idea',
                'description': 'The winning idea'
            }

    result = exporter.export_winning_idea(MockIdea())

    json_path = Path(result)
    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)

    assert data['name'] == 'Best Idea'


def test_export_winning_idea_with_evaluation(exporter):
    """Test exporting winning idea with evaluation."""
    class MockIdea:
        def model_dump(self):
            return {'id': 'winner', 'name': 'Winner'}

    class MockEval:
        def model_dump(self):
            return {'total_score': 95.0, 'rank': 1}

    result = exporter.export_winning_idea(MockIdea(), MockEval())

    json_path = Path(result)
    with open(json_path) as f:
        data = json.load(f)

    assert 'evaluation' in data
    assert data['evaluation']['total_score'] == 95.0


def test_export_run_summary(exporter):
    """Test exporting run summary."""
    stats = {
        'ideas_generated': 10,
        'execution_time': '5.2s',
        'status': 'completed'
    }

    result = exporter.export_run_summary(stats)

    # Returns the run directory
    assert Path(result).exists()

    # Check JSON file
    json_path = exporter.run_dir / "run_summary.json"
    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)

    assert data['ideas_generated'] == 10
    assert data['status'] == 'completed'
    assert 'timestamp' in data

    # Check markdown file
    md_path = exporter.run_dir / "README.md"
    assert md_path.exists()

    content = md_path.read_text()
    assert "Pipeline Run Summary" in content
    assert "ideas_generated" in content


def test_get_output_dir(exporter):
    """Test getting output directory."""
    output_dir = exporter.get_output_dir()

    assert output_dir == str(exporter.run_dir)
    assert Path(output_dir).exists()


def test_multiple_exports_separate_dirs():
    """Test multiple exporter instances create separate directories."""
    import time
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter1 = ResultsExporter(output_dir=tmpdir)
        time.sleep(1.1)  # Ensure different timestamps
        exporter2 = ResultsExporter(output_dir=tmpdir)

        # Should have different timestamps, thus different directories
        if exporter1.timestamp != exporter2.timestamp:
            assert exporter1.run_dir != exporter2.run_dir
        
        # Both should exist regardless
        assert exporter1.run_dir.exists()
        assert exporter2.run_dir.exists()


def test_export_creates_subdirectories():
    """Test exporter creates necessary subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = ResultsExporter(output_dir=str(Path(tmpdir) / "nested" / "path"))

        assert exporter.output_dir.exists()
        assert exporter.run_dir.exists()
