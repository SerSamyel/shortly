from datetime import UTC, datetime, timedelta

from tests.conftest import BASE_URL, create_link, signup


async def test_create_link_with_generated_code(client, auth):
    link = await create_link(client, auth, target_url="https://example.com/path")
    assert len(link["code"]) == 7
    assert link["short_url"] == f"{BASE_URL}/{link['code']}"
    assert link["target_url"] == "https://example.com/path"
    assert link["status"] == "active"
    assert link["is_active"] is True
    assert link["total_clicks"] == 0


async def test_create_link_with_alias_is_lowercased(client, auth):
    link = await create_link(client, auth, alias="My-Talk")
    assert link["code"] == "my-talk"
    assert link["short_url"] == f"{BASE_URL}/my-talk"


async def test_alias_taken_by_another_user_is_409(client, auth):
    await create_link(client, auth, alias="taken")
    other = await signup(client, "other@example.com")
    response = await client.post(
        "/api/links", json={"target_url": "https://example.org", "alias": "TAKEN"}, headers=other
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "This alias is already taken"


async def test_alias_of_a_deleted_link_is_never_reused(client, auth):
    link = await create_link(client, auth, alias="gone-forever")
    assert (await client.delete(f"/api/links/{link['id']}", headers=auth)).status_code == 204
    response = await client.post(
        "/api/links", json={"target_url": "https://example.org", "alias": "gone-forever"}, headers=auth
    )
    assert response.status_code == 409


async def test_reserved_and_malformed_aliases_are_rejected(client, auth):
    for alias, fragment in [("api", "reserved"), ("a_b", "only letters"), ("ab", "3 to 32")]:
        response = await client.post(
            "/api/links", json={"target_url": "https://example.com", "alias": alias}, headers=auth
        )
        assert response.status_code == 422, alias
        body = response.json()
        assert body["errors"][0]["field"] == "alias"
        assert fragment in body["detail"]


async def test_empty_alias_means_generated_code(client, auth):
    link = await create_link(client, auth, alias="")
    assert len(link["code"]) == 7


async def test_bad_target_urls_are_rejected(client, auth):
    for url in ["ftp://example.com", "javascript:alert(1)", f"{BASE_URL}/loop", "nonsense"]:
        response = await client.post("/api/links", json={"target_url": url}, headers=auth)
        assert response.status_code == 422, url
        assert response.json()["errors"][0]["field"] == "target_url"


async def test_expiration_must_be_in_the_future(client, auth):
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    response = await client.post(
        "/api/links", json={"target_url": "https://example.com", "expires_at": past}, headers=auth
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "expires_at"


async def test_link_with_future_expiration_is_active(client, auth):
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    link = await create_link(client, auth, expires_at=future)
    assert link["status"] == "active"
    assert link["expires_at"] is not None


async def test_rate_limit_returns_429(client, auth, settings):
    settings.links_per_minute = 3
    for _ in range(3):
        await create_link(client, auth)
    response = await client.post(
        "/api/links", json={"target_url": "https://example.com"}, headers=auth
    )
    assert response.status_code == 429


async def test_rate_limit_fails_open_when_cache_is_down(client, auth, store):
    store.fail = True
    response = await client.post(
        "/api/links", json={"target_url": "https://example.com"}, headers=auth
    )
    assert response.status_code == 201


async def test_list_shows_only_own_links_newest_first_with_pagination(client, auth):
    first = await create_link(client, auth, alias="first-one")
    second = await create_link(client, auth, alias="second-one")
    other = await signup(client, "other@example.com")
    await create_link(client, other, alias="not-mine")

    page = (await client.get("/api/links", headers=auth)).json()
    assert page["total"] == 2
    assert [item["id"] for item in page["items"]] == [second["id"], first["id"]]

    small = (await client.get("/api/links?page=2&page_size=1", headers=auth)).json()
    assert [item["id"] for item in small["items"]] == [first["id"]]
    assert small["page"] == 2 and small["page_size"] == 1


async def test_other_users_links_are_404(client, auth):
    link = await create_link(client, auth)
    other = await signup(client, "other@example.com")
    assert (await client.get(f"/api/links/{link['id']}", headers=other)).status_code == 404
    assert (
        await client.patch(f"/api/links/{link['id']}", json={"is_active": False}, headers=other)
    ).status_code == 404
    assert (await client.delete(f"/api/links/{link['id']}", headers=other)).status_code == 404
    assert (await client.get(f"/api/links/{link['id']}/stats", headers=other)).status_code == 404


async def test_disable_and_enable_a_link(client, auth):
    link = await create_link(client, auth)
    disabled = await client.patch(f"/api/links/{link['id']}", json={"is_active": False}, headers=auth)
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
    enabled = await client.patch(f"/api/links/{link['id']}", json={"is_active": True}, headers=auth)
    assert enabled.json()["status"] == "active"


async def test_deleted_link_disappears_from_the_list(client, auth):
    link = await create_link(client, auth)
    await client.delete(f"/api/links/{link['id']}", headers=auth)
    assert (await client.get("/api/links", headers=auth)).json()["total"] == 0
    assert (await client.get(f"/api/links/{link['id']}", headers=auth)).status_code == 404
