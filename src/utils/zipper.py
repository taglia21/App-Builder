import shutil
import os
from pathlib import Path

def zip_directory(source_dir: str, output_filename: str) -> str:
    """
    Zips a directory and returns the path to the zip file.
    
    Args:
        source_dir: Path to the directory to zip
        output_filename: Desired output filename (without extension)
        
    Returns:
        Path to the created zip file
    """
    source_path = Path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
        
    output_path = shutil.make_archive(output_filename, 'zip', source_dir)
    return output_path
