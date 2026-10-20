from shortly.privacy import referrer_domain, visitor_hash


def test_missing_referrer_is_direct():
    assert referrer_domain(None) == "direct"
    assert referrer_domain("") == "direct"
    assert referrer_domain("not a url") == "direct"


def test_referrer_is_reduced_to_domain_without_www():
    assert referrer_domain("https://www.Google.com/search?q=secret") == "google.com"
    assert referrer_domain("https://t.me/channel/123") == "t.me"


def test_referrer_from_own_host_counts_as_direct():
    assert referrer_domain("http://short.test/app", "short.test") == "direct"


def test_visitor_hash_is_stable_within_a_salt_and_hides_the_ip():
    first = visitor_hash("salt-a", "203.0.113.7", "Firefox")
    assert first == visitor_hash("salt-a", "203.0.113.7", "Firefox")
    assert first != visitor_hash("salt-b", "203.0.113.7", "Firefox")
    assert first != visitor_hash("salt-a", "203.0.113.8", "Firefox")
    assert "203.0.113.7" not in first
    assert len(first) == 64
