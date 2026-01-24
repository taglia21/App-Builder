"""
Rich Progress Indicators for Pipeline Execution

Provides beautiful console output with progress bars, spinners,
and real-time status updates using the 'rich' library.
"""

import time
from typing import Optional, List, Dict, Any, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.tree import Tree
from rich.markdown import Markdown
from rich.status import Status

console = Console()


class StageStatus(Enum):
    """Status of a pipeline stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStageInfo:
    """Information about a pipeline stage."""
    name: str
    description: str
    status: StageStatus = StageStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    items_total: int = 0
    items_completed: int = 0
    message: str = ""
    
    @property
    def duration(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None
    
    @property
    def duration_str(self) -> str:
        d = self.duration
        if d is None:
            return "-"
        if d < 60:
            return f"{d:.1f}s"
        return f"{int(d // 60)}m {int(d % 60)}s"


class PipelineProgress:
    """
    Rich progress display for pipeline execution.
    
    Usage:
        with PipelineProgress() as progress:
            progress.start_stage("intelligence")
            # ... do work ...
            progress.complete_stage("intelligence", items_generated=12)
    """
    
    STAGES = [
        PipelineStageInfo("intelligence", "Gathering Market Intelligence"),
        PipelineStageInfo("ideas", "Generating Startup Ideas"),
        PipelineStageInfo("scoring", "Scoring and Ranking Ideas"),
        PipelineStageInfo("prompt", "Generating Product Prompt"),
        PipelineStageInfo("refinement", "Refining to Gold Standard"),
        PipelineStageInfo("codegen", "Generating Codebase"),
        PipelineStageInfo("qa", "Running Quality Assurance"),
    ]
    
    def __init__(self, show_details: bool = True, verbose: bool = False):
        self.show_details = show_details
        self.verbose = verbose
        self.stages: Dict[str, PipelineStageInfo] = {
            s.name: PipelineStageInfo(s.name, s.description) 
            for s in self.STAGES
        }
        self.current_stage: Optional[str] = None
        self._progress: Optional[Progress] = None
        self._task_id = None
        self._live: Optional[Live] = None
        self._start_time = time.time()
        
    def __enter__(self):
        self._start_time = time.time()
        self._show_header()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._show_error(str(exc_val))
        else:
            self._show_summary()
        return False
    
    def _show_header(self):
        """Show pipeline header."""
        console.print()
        console.print(Panel.fit(
            "[bold blue]🚀 Startup Generator Pipeline[/bold blue]",
            border_style="blue",
        ))
        console.print()
    
    def _get_status_icon(self, status: StageStatus) -> str:
        """Get icon for status."""
        icons = {
            StageStatus.PENDING: "⏳",
            StageStatus.RUNNING: "🔄",
            StageStatus.COMPLETED: "✅",
            StageStatus.FAILED: "❌",
            StageStatus.SKIPPED: "⏭️",
        }
        return icons.get(status, "?")
    
    def _get_status_color(self, status: StageStatus) -> str:
        """Get color for status."""
        colors = {
            StageStatus.PENDING: "dim",
            StageStatus.RUNNING: "yellow",
            StageStatus.COMPLETED: "green",
            StageStatus.FAILED: "red",
            StageStatus.SKIPPED: "dim",
        }
        return colors.get(status, "white")
    
    def start_stage(self, stage_name: str, total_items: int = 0):
        """Start a pipeline stage."""
        if stage_name not in self.stages:
            return
        
        # End previous stage if any
        if self.current_stage and self.current_stage != stage_name:
            prev = self.stages[self.current_stage]
            if prev.status == StageStatus.RUNNING:
                prev.status = StageStatus.COMPLETED
                prev.end_time = time.time()
        
        self.current_stage = stage_name
        stage = self.stages[stage_name]
        stage.status = StageStatus.RUNNING
        stage.start_time = time.time()
        stage.items_total = total_items
        stage.items_completed = 0
        
        # Find stage number
        stage_num = list(self.stages.keys()).index(stage_name) + 1
        total_stages = len(self.stages)
        
        console.print(
            f"  [{self._get_status_color(StageStatus.RUNNING)}]"
            f"{self._get_status_icon(StageStatus.RUNNING)}[/] "
            f"[bold cyan]Stage {stage_num}/{total_stages}:[/] "
            f"{stage.description}..."
        )
    
    def update_stage(self, items_completed: int = None, message: str = None):
        """Update current stage progress."""
        if not self.current_stage:
            return
        
        stage = self.stages[self.current_stage]
        if items_completed is not None:
            stage.items_completed = items_completed
        if message:
            stage.message = message
            if self.verbose:
                console.print(f"    [dim]→ {message}[/]")
    
    def complete_stage(self, stage_name: str = None, items_generated: int = None, message: str = None):
        """Mark a stage as completed."""
        stage_name = stage_name or self.current_stage
        if not stage_name or stage_name not in self.stages:
            return
        
        stage = self.stages[stage_name]
        stage.status = StageStatus.COMPLETED
        stage.end_time = time.time()
        if items_generated:
            stage.items_completed = items_generated
        if message:
            stage.message = message
        
        # Show completion
        info_parts = []
        if stage.items_completed:
            info_parts.append(f"{stage.items_completed} items")
        info_parts.append(stage.duration_str)
        
        info_str = ", ".join(info_parts)
        console.print(
            f"    [{self._get_status_color(StageStatus.COMPLETED)}]"
            f"{self._get_status_icon(StageStatus.COMPLETED)} "
            f"Completed ({info_str})[/]"
        )
    
    def fail_stage(self, stage_name: str = None, error: str = None):
        """Mark a stage as failed."""
        stage_name = stage_name or self.current_stage
        if not stage_name or stage_name not in self.stages:
            return
        
        stage = self.stages[stage_name]
        stage.status = StageStatus.FAILED
        stage.end_time = time.time()
        stage.message = error or "Unknown error"
        
        console.print(
            f"    [{self._get_status_color(StageStatus.FAILED)}]"
            f"{self._get_status_icon(StageStatus.FAILED)} "
            f"Failed: {error or 'Unknown error'}[/]"
        )
    
    def skip_stage(self, stage_name: str, reason: str = "Skipped"):
        """Mark a stage as skipped."""
        if stage_name not in self.stages:
            return
        
        stage = self.stages[stage_name]
        stage.status = StageStatus.SKIPPED
        stage.message = reason
        
        stage_num = list(self.stages.keys()).index(stage_name) + 1
        total_stages = len(self.stages)
        
        console.print(
            f"  [{self._get_status_color(StageStatus.SKIPPED)}]"
            f"{self._get_status_icon(StageStatus.SKIPPED)} "
            f"Stage {stage_num}/{total_stages}: {stage.description} - {reason}[/]"
        )
    
    def _show_error(self, error: str):
        """Show error panel."""
        console.print()
        console.print(Panel(
            f"[bold red]Pipeline Failed[/bold red]\n\n{error}",
            title="❌ Error",
            border_style="red",
        ))
    
    def _show_summary(self):
        """Show final summary."""
        console.print()
        
        total_time = time.time() - self._start_time
        completed = sum(1 for s in self.stages.values() if s.status == StageStatus.COMPLETED)
        failed = sum(1 for s in self.stages.values() if s.status == StageStatus.FAILED)
        
        # Summary table
        table = Table(title="Pipeline Summary", show_header=True, header_style="bold cyan")
        table.add_column("Stage", style="dim")
        table.add_column("Status")
        table.add_column("Duration", justify="right")
        table.add_column("Details")
        
        for stage in self.stages.values():
            status_text = Text()
            status_text.append(f"{self._get_status_icon(stage.status)} ")
            status_text.append(
                stage.status.value.capitalize(),
                style=self._get_status_color(stage.status)
            )
            
            details = stage.message or ""
            if stage.items_completed and stage.status == StageStatus.COMPLETED:
                details = f"{stage.items_completed} items"
            
            table.add_row(
                stage.description,
                status_text,
                stage.duration_str,
                details,
            )
        
        console.print(table)
        
        # Final status
        if failed == 0:
            console.print()
            console.print(Panel.fit(
                f"[bold green]✅ Pipeline Completed Successfully[/bold green]\n"
                f"Total time: {total_time:.1f}s | Stages: {completed}/{len(self.stages)}",
                border_style="green",
            ))
        else:
            console.print()
            console.print(Panel.fit(
                f"[bold red]❌ Pipeline Completed with Errors[/bold red]\n"
                f"Total time: {total_time:.1f}s | Completed: {completed} | Failed: {failed}",
                border_style="red",
            ))


class FileGenerationProgress:
    """Progress display for file generation."""
    
    def __init__(self, total_files: int = 0):
        self.total_files = total_files
        self.generated_files = 0
        self._progress: Optional[Progress] = None
        self._task_id = None
    
    def __enter__(self):
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        )
        self._progress.__enter__()
        self._task_id = self._progress.add_task(
            "Generating files...",
            total=self.total_files or 100,
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._progress:
            self._progress.__exit__(exc_type, exc_val, exc_tb)
        return False
    
    def set_total(self, total: int):
        """Set total number of files."""
        self.total_files = total
        if self._progress and self._task_id is not None:
            self._progress.update(self._task_id, total=total)
    
    def add_file(self, filename: str, category: str = ""):
        """Record a generated file."""
        self.generated_files += 1
        if self._progress and self._task_id is not None:
            desc = f"[cyan]{category}[/] {filename}" if category else filename
            self._progress.update(
                self._task_id,
                advance=1,
                description=f"Generated: {desc}"
            )
    
    def complete(self):
        """Mark generation as complete."""
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                completed=self.total_files,
                description="[green]Generation complete![/]"
            )


@contextmanager
def spinner(message: str):
    """Simple spinner context manager for quick operations."""
    with console.status(f"[bold cyan]{message}[/]") as status:
        yield status


def print_success(message: str):
    """Print a success message."""
    console.print(f"[green]✅ {message}[/]")


def print_error(message: str):
    """Print an error message."""
    console.print(f"[red]❌ {message}[/]")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[yellow]⚠️ {message}[/]")


def print_info(message: str):
    """Print an info message."""
    console.print(f"[blue]ℹ️ {message}[/]")


def show_generated_files(files: List[str], output_dir: str):
    """Display a tree of generated files."""
    tree = Tree(f"📁 [bold]{output_dir}[/]")
    
    # Group files by directory
    dirs: Dict[str, List[str]] = {}
    for filepath in sorted(files):
        parts = filepath.split("/")
        if len(parts) > 1:
            dir_name = "/".join(parts[:-1])
            filename = parts[-1]
        else:
            dir_name = "."
            filename = filepath
        
        if dir_name not in dirs:
            dirs[dir_name] = []
        dirs[dir_name].append(filename)
    
    # Build tree
    for dir_name in sorted(dirs.keys()):
        if dir_name == ".":
            branch = tree
        else:
            branch = tree.add(f"📂 {dir_name}")
        
        for filename in dirs[dir_name]:
            # Determine icon based on extension
            ext = filename.split(".")[-1] if "." in filename else ""
            icons = {
                "py": "🐍",
                "ts": "📘",
                "tsx": "⚛️",
                "js": "📒",
                "json": "📋",
                "md": "📝",
                "yml": "⚙️",
                "yaml": "⚙️",
                "toml": "⚙️",
                "css": "🎨",
                "html": "🌐",
                "sql": "🗄️",
                "sh": "🖥️",
                "bat": "🖥️",
            }
            icon = icons.get(ext, "📄")
            branch.add(f"{icon} {filename}")
    
    console.print(tree)


def show_idea_selection(ideas: List[Dict[str, Any]], selected_index: int = 0):
    """Display idea selection with scores."""
    console.print()
    console.print("[bold cyan]Top Startup Ideas:[/]")
    console.print()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", width=30)
    table.add_column("Score", justify="right", width=8)
    table.add_column("One-liner", width=50)
    
    for i, idea in enumerate(ideas[:5]):
        style = "bold green" if i == selected_index else ""
        marker = "→" if i == selected_index else " "
        
        score = idea.get('score', idea.get('total_score', 0))
        if isinstance(score, (int, float)):
            score_str = f"{score:.1f}"
        else:
            score_str = str(score)
        
        table.add_row(
            f"{marker}{i+1}",
            idea.get('name', 'Unknown')[:30],
            score_str,
            (idea.get('one_liner', '')[:47] + '...') if len(idea.get('one_liner', '')) > 50 else idea.get('one_liner', ''),
            style=style,
        )
    
    console.print(table)
    console.print()
