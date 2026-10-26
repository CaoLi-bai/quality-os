from quality_os.healing import inspect_candidate, propose_healing

ORIGINAL = '''def test_refund(page):
    page.get_by_test_id("refund-submit").click()
    assert page.status == "success"
'''


def test_locator_only_candidate_is_allowed_but_not_merged(tmp_path):
    source = tmp_path / "test_ui.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    report = propose_healing(source, tmp_path / "out", "refund-submit", "confirm-refund", "propose")
    assert report["status"] == "pending_human_review"
    assert report["auto_merge"] is False
    assert (tmp_path / "out" / "candidate.diff").exists()


def test_locator_change_is_intent_preserving():
    candidate = ORIGINAL.replace("refund-submit", "confirm-refund")
    assert inspect_candidate(ORIGINAL, candidate)["passed"] is True


def test_assertion_change_is_blocked():
    candidate = ORIGINAL.replace('"success"', '"failed"').replace("refund-submit", "confirm-refund")
    assert inspect_candidate(ORIGINAL, candidate)["passed"] is False


def test_skip_and_deletion_are_blocked():
    assert inspect_candidate(ORIGINAL, "def test_refund(page):\n    pass\n")["passed"] is False
    skipped = ORIGINAL.replace("def test_refund", "@pytest.mark.skip\ndef test_refund")
    assert inspect_candidate(ORIGINAL, skipped)["passed"] is False
