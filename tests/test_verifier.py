from agents.verifier import verify_file_exists,verify_folder_exists
def test_verifiers(tmp_path):
    (tmp_path/"a.txt").write_text("ok");(tmp_path/"folder").mkdir()
    assert verify_file_exists(tmp_path,"a.txt") and verify_folder_exists(tmp_path,"folder")
    assert not verify_file_exists(tmp_path,"missing.txt")
