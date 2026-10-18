"""Independent filesystem verification."""
from pathlib import Path
def _inside(root,relative):
    root=Path(root).resolve(); target=(root/relative).resolve()
    return target if target==root or root in target.parents else None
def verify_file_exists(root:Path,relative_path:str)->bool:
    p=_inside(root,relative_path); return bool(p and p.is_file())
def verify_folder_exists(root:Path,relative_path:str)->bool:
    p=_inside(root,relative_path); return bool(p and p.is_dir())
