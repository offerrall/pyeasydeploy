import fnmatch
import os
from pathlib import PurePosixPath, Path
from fabric import Connection

DEFAULT_IGNORE = [".git", ".venv", "venv", "__pycache__", ".vscode", ".idea", ".pytest_cache", ".mypy_cache", ".ruff_cache", "*.pyc", "*.pyo", "*.db", "*.sqlite", "*.sqlite3", ".DS_Store"]

def upload_file(conn: Connection, local_file: str, remote_file: str, verbose: bool = True, remove_if_exists: bool = True):
    local_path = Path(local_file)
    if not local_path.exists():
        raise FileNotFoundError(f"Local file not found: {local_file}")

    if remove_if_exists:
        conn.run(f"rm -f {remote_file}", hide=True, warn=True)
    
    remote_dir = str(PurePosixPath(remote_file).parent)
    conn.run(f"mkdir -p {remote_dir}", hide=True)
    
    if verbose: print(f"Uploading {local_file} to {remote_file}")
    conn.put(str(local_path), remote_file)
    if verbose: print(f"Upload complete")

def upload_directory(conn: Connection, local_dir: str, remote_dir: str, verbose: bool = True, remove_if_exists: bool = True, ignore: list[str] | None = None):
    local_path = Path(local_dir)
    if not local_path.exists():
        raise FileNotFoundError(f"Local directory not found: {local_dir}")

    patterns = DEFAULT_IGNORE if ignore is None else ignore

    if remove_if_exists:
        conn.run(f"rm -rf {remote_dir}", hide=True, warn=True)
    
    conn.run(f"mkdir -p {remote_dir}", hide=True)
    
    if verbose: print(f"Uploading {local_dir} to {remote_dir}")
    
    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, p) for p in patterns)]

        relative_root = Path(root).relative_to(local_path)
        remote_root = f"{remote_dir}/{relative_root}".replace("\\", "/")
        
        for dir_name in dirs:
            conn.run(f"mkdir -p {remote_root}/{dir_name}", hide=True)
        
        for file_name in files:
            if any(fnmatch.fnmatch(file_name, p) for p in patterns):
                continue
            local_file = Path(root) / file_name
            remote_file = f"{remote_root}/{file_name}".replace("\\", "/")
            conn.put(str(local_file), remote_file)
    
    if verbose: print(f"Upload complete")