import pytest
from automation.filesystem import SandboxFilesystem,FileOperationError
def test_escape_blocked(tmp_path):
    fs=SandboxFilesystem(tmp_path)
    with pytest.raises(FileOperationError):fs.resolve("../outside.txt")
def test_no_overwrite(tmp_path):
    fs=SandboxFilesystem(tmp_path);(tmp_path/"x.txt").write_text("old")
    with pytest.raises(FileOperationError):fs.rename_file("x.txt","x.txt")
