"""
Unit tests for progress indicator utilities.

Tests cover:
- PipelineProgress context manager
- FileGenerationProgress
- Spinner functionality
- Display helpers
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import time

from src.utils.progress import (
    PipelineProgress,
    FileGenerationProgress,
    StageStatus,
    spinner,
    print_success,
    print_error,
    print_warning,
    print_info,
    show_generated_files,
    show_idea_selection,
)


class TestStageStatus:
    """Tests for StageStatus enum."""
    
    def test_status_values(self):
        """Test all status values exist."""
        assert StageStatus.PENDING.value == "pending"
        assert StageStatus.RUNNING.value == "running"
        assert StageStatus.COMPLETED.value == "completed"
        assert StageStatus.FAILED.value == "failed"
        assert StageStatus.SKIPPED.value == "skipped"
    
    def test_status_comparison(self):
        """Test status enum comparison."""
        assert StageStatus.COMPLETED != StageStatus.FAILED
        assert StageStatus.RUNNING == StageStatus.RUNNING


class TestPipelineProgress:
    """Tests for PipelineProgress context manager."""
    
    def test_initialization(self):
        """Test PipelineProgress initializes correctly."""
        progress = PipelineProgress()
        
        # Uses predefined STAGES
        assert len(progress.stages) > 0
        assert all(s.status == StageStatus.PENDING for s in progress.stages.values())
    
    def test_context_manager_enter(self):
        """Test context manager entry."""
        with PipelineProgress() as progress:
            assert progress is not None
    
    def test_start_stage(self):
        """Test starting a stage."""
        progress = PipelineProgress()
        
        # Use one of the predefined stages
        progress.start_stage("intelligence")
        
        assert progress.stages["intelligence"].status == StageStatus.RUNNING
        assert progress.current_stage == "intelligence"
    
    def test_complete_stage(self):
        """Test completing a stage."""
        progress = PipelineProgress()
        
        progress.start_stage("intelligence")
        progress.complete_stage("intelligence")
        
        assert progress.stages["intelligence"].status == StageStatus.COMPLETED
    
    def test_fail_stage(self):
        """Test failing a stage."""
        progress = PipelineProgress()
        
        progress.start_stage("intelligence")
        progress.fail_stage("intelligence", "Test error")
        
        assert progress.stages["intelligence"].status == StageStatus.FAILED
    
    def test_skip_stage(self):
        """Test skipping a stage."""
        progress = PipelineProgress()
        
        progress.skip_stage("intelligence", "Not needed")
        
        assert progress.stages["intelligence"].status == StageStatus.SKIPPED
    
    def test_timing_tracked(self):
        """Test that stage timing is tracked."""
        progress = PipelineProgress()
        
        progress.start_stage("intelligence")
        time.sleep(0.01)  # Small delay
        progress.complete_stage("intelligence")
        
        # Timing should be recorded
        stage = progress.stages["intelligence"]
        assert stage.duration is not None
        assert stage.duration >= 0.01
    
    def test_invalid_stage_name(self):
        """Test handling invalid stage names."""
        progress = PipelineProgress()
        
        # Should not raise, but should handle gracefully
        progress.start_stage("Nonexistent Stage")
    
    def test_multiple_stages_workflow(self):
        """Test complete workflow with multiple stages."""
        with PipelineProgress() as progress:
            progress.start_stage("intelligence")
            progress.complete_stage("intelligence")
            
            progress.start_stage("ideas")
            progress.complete_stage("ideas")
            
            progress.start_stage("scoring")
            progress.complete_stage("scoring")
        
        assert progress.stages["intelligence"].status == StageStatus.COMPLETED
        assert progress.stages["ideas"].status == StageStatus.COMPLETED
        assert progress.stages["scoring"].status == StageStatus.COMPLETED


class TestFileGenerationProgress:
    """Tests for FileGenerationProgress."""
    
    def test_initialization(self):
        """Test FileGenerationProgress initializes correctly."""
        progress = FileGenerationProgress(total_files=10)
        
        assert progress.total_files == 10
        assert progress.generated_files == 0
    
    def test_add_file(self):
        """Test adding a generated file."""
        with FileGenerationProgress(total_files=5) as progress:
            progress.add_file("test.py")
            assert progress.generated_files == 1
    
    def test_multiple_files(self):
        """Test adding multiple files."""
        with FileGenerationProgress(total_files=3) as progress:
            progress.add_file("file1.py")
            progress.add_file("file2.py")
            progress.add_file("file3.py")
            assert progress.generated_files == 3
    
    def test_context_manager(self):
        """Test using as context manager."""
        with FileGenerationProgress(total_files=2) as progress:
            progress.add_file("file1.py")
            progress.add_file("file2.py")
        
        assert progress.generated_files == 2


class TestSpinner:
    """Tests for spinner context manager."""
    
    def test_spinner_context_manager(self):
        """Test spinner as context manager."""
        with spinner("Testing...") as s:
            # Should not raise
            pass
    
    def test_spinner_with_work(self):
        """Test spinner with actual work."""
        result = None
        
        with spinner("Processing..."):
            result = 1 + 1
        
        assert result == 2
    
    def test_spinner_on_error(self):
        """Test spinner handles errors gracefully."""
        with pytest.raises(ValueError):
            with spinner("Will fail..."):
                raise ValueError("Test error")


class TestPrintHelpers:
    """Tests for print helper functions."""
    
    @patch('src.utils.progress.console')
    def test_print_success(self, mock_console):
        """Test print_success function."""
        print_success("Operation completed")
        
        mock_console.print.assert_called()
    
    @patch('src.utils.progress.console')
    def test_print_error(self, mock_console):
        """Test print_error function."""
        print_error("Something went wrong")
        
        mock_console.print.assert_called()
    
    @patch('src.utils.progress.console')
    def test_print_warning(self, mock_console):
        """Test print_warning function."""
        print_warning("Be careful")
        
        mock_console.print.assert_called()
    
    @patch('src.utils.progress.console')
    def test_print_info(self, mock_console):
        """Test print_info function."""
        print_info("For your information")
        
        mock_console.print.assert_called()


class TestShowGeneratedFiles:
    """Tests for show_generated_files function."""
    
    @patch('src.utils.progress.console')
    def test_show_files_list(self, mock_console):
        """Test showing a list of generated files."""
        files = [
            "app/main.py",
            "app/models.py",
            "requirements.txt",
        ]
        
        show_generated_files(files, "/output")
        
        mock_console.print.assert_called()
    
    @patch('src.utils.progress.console')
    def test_show_empty_list(self, mock_console):
        """Test showing an empty file list."""
        show_generated_files([], "/output")
        
        # Should handle gracefully


class TestShowIdeaSelection:
    """Tests for show_idea_selection function."""
    
    @patch('src.utils.progress.console')
    def test_show_ideas(self, mock_console):
        """Test showing idea selection."""
        ideas = [
            {"name": "Idea 1", "description": "First idea"},
            {"name": "Idea 2", "description": "Second idea"},
        ]
        
        show_idea_selection(ideas)
        
        mock_console.print.assert_called()
    
    @patch('src.utils.progress.console')
    def test_show_ideas_with_scores(self, mock_console):
        """Test showing ideas with scores."""
        ideas = [
            {"name": "Idea 1", "description": "First idea", "score": 85},
            {"name": "Idea 2", "description": "Second idea", "score": 72},
        ]
        
        show_idea_selection(ideas)
        
        mock_console.print.assert_called()


class TestProgressIntegration:
    """Integration tests for progress indicators."""
    
    def test_nested_progress(self):
        """Test using progress indicators in nested context."""
        with PipelineProgress() as outer:
            outer.start_stage("intelligence")
            outer.complete_stage("intelligence")
            
            outer.start_stage("codegen")
            with FileGenerationProgress(total_files=2) as file_progress:
                file_progress.add_file("file1.py")
                file_progress.add_file("file2.py")
            outer.complete_stage("codegen")
        
        assert outer.stages["codegen"].status == StageStatus.COMPLETED
        assert file_progress.generated_files == 2
    
    def test_error_recovery(self):
        """Test progress recovery after error."""
        try:
            with PipelineProgress() as progress:
                progress.start_stage("intelligence")
                raise RuntimeError("Simulated error")
        except RuntimeError:
            pass
        
        # Progress should still be accessible
        assert progress.stages["intelligence"].status == StageStatus.RUNNING
