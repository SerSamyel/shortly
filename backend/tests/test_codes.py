import pytest

from shortly.codes import CODE_LENGTH, alias_error, generate_code, target_url_error


def test_generated_code_is_seven_lowercase_alphanumerics():
    for _ in range(200):
        code = generate_code()
        assert len(code) == CODE_LENGTH
        assert code.isalnum() and code == code.lower()


@pytest.mark.parametrize("alias", ["abc", "my-talk", "a1-b2-c3", "x" * 32])
def test_valid_aliases(alias):
    assert alias_error(alias) is None


@pytest.mark.parametrize(
    ("alias", "fragment"),
    [
        ("ab", "3 to 32"),
        ("x" * 33, "3 to 32"),
        ("-abc", "cannot start or end"),
        ("abc-", "cannot start or end"),
        ("ab_c", "only letters"),
        ("api", "reserved"),
        ("login", "reserved"),
    ],
)
def test_invalid_aliases(alias, fragment):
    assert fragment in alias_error(alias)


@pytest.mark.parametrize(
    "url", ["https://example.com", "http://example.com/a?b=c#d", "https://sub.example.co.uk:8443/x"]
)
def test_valid_target_urls(url):
    assert target_url_error(url, "short.test") is None


@pytest.mark.parametrize(
    ("url", "fragment"),
    [
        ("ftp://example.com/file", "Only http and https"),
        ("javascript:alert(1)", "Only http and https"),
        ("https://", "must include a host"),
        ("https://exa mple.com", "spaces"),
        ("https://short.test/abc", "this service"),
        ("https://SHORT.test/abc", "this service"),
        ("https://example.com/" + "a" * 2048, "at most 2048"),
    ],
)
def test_invalid_target_urls(url, fragment):
    assert fragment in target_url_error(url, "short.test")
