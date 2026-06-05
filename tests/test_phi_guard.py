from healthcare_agents.safety.phi_guard import PHIGuard, redact_phi


def test_redact_ssn():
    result = redact_phi("Patient SSN is 123-45-6789")
    assert "[REDACTED_SSN]" in result.text
    assert "123-45-6789" not in result.text
    assert len(result.redactions) == 1


def test_redact_email():
    result = redact_phi("Contact: patient@example.com")
    assert "[REDACTED_EMAIL]" in result.text


def test_phi_guard_disabled():
    guard = PHIGuard(enabled=False)
    text = "SSN: 123-45-6789"
    assert guard.sanitize(text) == text


def test_phi_guard_enabled():
    guard = PHIGuard(enabled=True)
    text = "SSN: 123-45-6789"
    assert "[REDACTED_SSN]" in guard.sanitize(text)
