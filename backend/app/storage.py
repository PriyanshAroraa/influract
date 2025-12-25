"""
Local JSON storage for contract analyses.
Stores data in ./data directory as JSON files.
"""
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from app.config import get_settings

settings = get_settings()


def get_data_dir() -> Path:
    """Get the data directory, creating it if it doesn't exist."""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(exist_ok=True)
    return data_dir


def save_analysis(analysis: Dict[str, Any]) -> str:
    """Save an analysis to a JSON file. Returns the analysis ID."""
    analysis_id = str(uuid.uuid4())
    analysis["id"] = analysis_id
    analysis["created_at"] = datetime.utcnow().isoformat()
    
    file_path = get_data_dir() / f"{analysis_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    return analysis_id


def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an analysis by ID."""
    file_path = get_data_dir() / f"{analysis_id}.json"
    if not file_path.exists():
        return None
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_analyses() -> list[Dict[str, Any]]:
    """List all saved analyses (metadata only)."""
    data_dir = get_data_dir()
    analyses = []
    
    for file_path in data_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                analyses.append({
                    "id": data.get("id"),
                    "created_at": data.get("created_at"),
                    "filename": data.get("filename"),
                    "summary": data.get("summary", {})
                })
        except Exception:
            continue
    
    # Sort by created_at descending
    analyses.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return analyses
