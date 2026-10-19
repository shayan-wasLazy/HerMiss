"""Workspace-constrained filesystem operations."""
from collections import defaultdict
from pathlib import Path
import hashlib
import shutil


class FileOperationError(RuntimeError):
    pass


class SandboxFilesystem:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative: str) -> Path:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise FileOperationError("Unsafe relative path.")
        p = (self.root / relative_path).resolve()
        if p != self.root and self.root not in p.parents:
            raise FileOperationError("Path escapes workspace.")
        return p

    def create_folder(self, name: str) -> bool:
        p = self.resolve(name)
        if p.exists():
            if p.is_dir():
                return False
            raise FileOperationError("A file already uses this name.")
        p.mkdir(parents=False)
        return True

    def find_file(self, name: str):
        p = self.resolve(name)
        if p.is_file():
            return p
        matches = list(self.root.rglob(name))
        return matches[0] if matches else None

    def rename_file(self, source: str, destination: str) -> Path:
        a, b = self.resolve(source), self.resolve(destination)
        if not a.is_file():
            raise FileOperationError(f"Source file not found: {source}")
        if b.exists():
            raise FileOperationError("Destination already exists; refusing to overwrite.")
        return a.rename(b)

    def move_file(self, source: str, folder: str) -> Path:
        a, d = self.resolve(source), self.resolve(folder)
        if not a.is_file():
            raise FileOperationError(f"Source file not found: {source}")
        if not d.is_dir():
            raise FileOperationError(f"Destination folder not found: {folder}")
        b = self.resolve(str(Path(folder) / a.name))
        if b.exists():
            raise FileOperationError("Destination already exists; refusing to overwrite.")
        shutil.move(str(a), str(b))
        return b

    def organize_by_type(self) -> dict:
        """Move top-level files into extension-based categories without overwriting."""
        categories = {
            "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"},
            "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".ppt", ".pptx", ".xls", ".xlsx", ".csv"},
            "Code": {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".toml", ".sql", ".sh"},
            "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
            "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg"},
            "Video": {".mp4", ".mov", ".mkv", ".avi", ".webm"},
        }
        moved, skipped = [], []
        for source in sorted(self.root.iterdir()):
            if not source.is_file():
                continue
            category = next((n for n, exts in categories.items() if source.suffix.lower() in exts), "Other")
            destination_dir = self.root / category
            destination_dir.mkdir(exist_ok=True)
            destination = destination_dir / source.name
            if destination.exists():
                skipped.append(source.name)
                continue
            shutil.move(str(source), str(destination))
            moved.append({"file": source.name, "category": category})
        return {"moved": moved, "skipped": skipped, "count": len(moved)}

    def audit_workspace(self) -> dict:
        """Return file counts, extension counts, total size, and duplicate-content groups."""
        files = [p for p in self.root.rglob("*") if p.is_file()]
        extension_counts = defaultdict(int)
        hashes = defaultdict(list)
        total_bytes = 0
        for path in files:
            extension_counts[path.suffix.lower() or "[no extension]"] += 1
            try:
                hashes[hashlib.sha256(path.read_bytes()).hexdigest()].append(str(path.relative_to(self.root)))
                total_bytes += path.stat().st_size
            except OSError:
                continue
        duplicates = [group for group in hashes.values() if len(group) > 1]
        return {
            "file_count": len(files),
            "folder_count": sum(p.is_dir() for p in self.root.rglob("*")),
            "total_bytes": total_bytes,
            "extensions": dict(sorted(extension_counts.items())),
            "duplicate_groups": duplicates,
        }

    def list_directory(self):
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
