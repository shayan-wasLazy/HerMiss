"""Sandbox-constrained filesystem operations."""
from pathlib import Path
import shutil
class FileOperationError(RuntimeError): pass
class SandboxFilesystem:
    def __init__(self,root:Path):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
    def resolve(self,relative:str)->Path:
        p=(self.root/relative).resolve()
        if p!=self.root and self.root not in p.parents: raise FileOperationError("Path escapes sandbox.")
        if Path(relative).is_absolute() or ".." in Path(relative).parts: raise FileOperationError("Unsafe relative path.")
        return p
    def create_folder(self,name:str)->bool:
        p=self.resolve(name)
        if p.exists():
            if p.is_dir(): return False
            raise FileOperationError("A file already uses this name.")
        p.mkdir(parents=False); return True
    def find_file(self,name:str):
        p=self.resolve(name)
        if p.is_file(): return p
        matches=list(self.root.rglob(name))
        return matches[0] if matches else None
    def rename_file(self,source:str,destination:str)->Path:
        a=self.resolve(source); b=self.resolve(destination)
        if not a.is_file(): raise FileOperationError(f"Source file not found: {source}")
        if b.exists(): raise FileOperationError("Destination already exists; refusing to overwrite.")
        return a.rename(b)
    def move_file(self,source:str,folder:str)->Path:
        a=self.resolve(source); d=self.resolve(folder)
        if not a.is_file(): raise FileOperationError(f"Source file not found: {source}")
        if not d.is_dir(): raise FileOperationError(f"Destination folder not found: {folder}")
        b=self.resolve(str(Path(folder)/a.name))
        if b.exists(): raise FileOperationError("Destination already exists; refusing to overwrite.")
        return shutil.move(str(a),str(b)) and b
    def list_directory(self):
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
