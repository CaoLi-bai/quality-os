from quality_os.triage import classify_failure


def test_locator_failure_can_only_enter_reviewed_healing():
    category, _, allowed = classify_failure("Timeout waiting for locator data-testid=refund-submit")
    assert category == "locator_drift"
    assert allowed is True


def test_assertion_and_unknown_failures_stop_automation():
    assert classify_failure("assert 200 == 400")[2] is False
    assert classify_failure("unclassified internal state")[0] == "unknown"
    assert classify_failure("unclassified internal state")[2] is False


def test_connection_failure_is_environment():
    assert classify_failure("Connection refused by test server")[0] == "environment"
