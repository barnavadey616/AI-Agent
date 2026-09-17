"""
File manipulation, inspection, and organization tools for agents.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import shutil
import hashlib
import os
import json
from taskflow.core.tool import tool
from taskflow import config

@tool(name="scan_directory", description="Scan a directory and return file names, sizes, extensions, and timestamps.")
def scan_directory(directory_path: str) -> List[Dict[str, Any]]:
    """Lists files in the directory with metadata."""
    p = Path(directory_path)
    if not p.is_absolute():
        p = config.BASE_DIR / p
    if not p.exists() or not p.is_dir():
        return [{"error": f"Directory '{directory_path}' does not exist."}]

    results = []
    for item in p.iterdir():
        if item.is_file():
            stat = item.stat()
            results.append({
                "name": item.name,
                "path": str(item.resolve()),
                "size_bytes": stat.st_size,
                "extension": item.suffix.lower(),
                "modified_time": stat.st_mtime
            })
    return results

@tool(name="read_file_snippet", description="Read the first N characters of a text/csv/code file.")
def read_file_snippet(file_path: str, max_chars: int = 2000) -> str:
    """Reads a preview snippet of the file to inspect content."""
    p = Path(file_path)
    if not p.is_absolute():
        p = config.BASE_DIR / p
    if not p.exists():
        return f"Error: File '{file_path}' not found."

    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(max_chars)
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool(name="organize_file", description="Move and rename a file into a categorized target folder.")
def organize_file(source_path: str, category: str, new_filename: Optional[str] = None, target_base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Moves a file to target_base_dir/category with optional clean renaming."""
    src = Path(source_path)
    if not src.is_absolute():
        src = config.BASE_DIR / src
    if not src.exists():
        return {"success": False, "error": f"Source file '{source_path}' does not exist."}

    dest_base = Path(target_base_dir) if target_base_dir else config.ORGANIZED_DIR
    if not dest_base.is_absolute():
        dest_base = config.BASE_DIR / dest_base

    target_folder = dest_base / category
    target_folder.mkdir(parents=True, exist_ok=True)

    filename = new_filename or src.name
    dest_path = target_folder / filename

    # Prevent collision
    counter = 1
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    while dest_path.exists():
        dest_path = target_folder / f"{stem}_{counter}{suffix}"
        counter += 1

    shutil.move(str(src), str(dest_path))
    return {
        "success": True,
        "original_path": str(src),
        "new_path": str(dest_path),
        "category": category,
        "filename": dest_path.name
    }

@tool(name="generate_manifest", description="Save an organization summary and audit log as JSON and Markdown.")
def generate_manifest(records: List[Dict[str, Any]], manifest_filename: str = "organization_manifest.json") -> str:
    """Saves records of organized files for auditing."""
    output_path = config.REPORTS_DIR / manifest_filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    # Also write a clean markdown summary
    md_path = output_path.with_suffix(".md")
    lines = [
        "# File Organization Audit Report",
        f"Total Files Processed: {len(records)}\n",
        "| Original File | New Category | New Filename | Status |",
        "|---|---|---|---|"
    ]
    for r in records:
        orig = Path(r.get("original_path", "")).name
        cat = r.get("category", "Unsorted")
        new_name = r.get("filename", "")
        status = "✅ Success" if r.get("success", True) else "❌ Failed"
        lines.append(f"| `{orig}` | **{cat}** | `{new_name}` | {status} |")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return f"Manifest and Markdown report saved to: {md_path}"
