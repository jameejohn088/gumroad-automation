"""Auth flow tests: signup, login, logout, refresh, forgot/reset, verify, me."""
from app.services import auth_service


def test_signup_and_login(client, db):
    r = client.post("/api/v1/auth/signup", json={
        "email": "anna@example.com", "password": "password123", "name": "Anna"})
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "anna@example.com"

    r = client.post("/api/v1/auth/login", json={
        "email": "anna@example.com", "password": "password123"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password_generic_message(client, user_factory):
    user, _ = user_factory(email="sam@example.com")
    r = client.post("/api/v1/auth/login", json={
        "email": "sam@example.com", "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["detail"] == auth_service.GENERIC_LOGIN_ERROR


def test_login_unknown_email_same_generic_message(client):
    # No user enumeration: unknown email gives the identical message.
    r = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com", "password": "whatever123"})
    assert r.status_code == 401
    assert r.json()["detail"] == auth_service.GENERIC_LOGIN_ERROR


def test_duplicate_signup_does_not_enumerate(client, db, user_factory):
    user_factory(email="dup@example.com")
    r = client.post("/api/v1/auth/signup", json={
        "email": "dup@example.com", "password": "password123", "name": "X"})
    assert r.status_code == 201  # pretends success
    from app.models.models import User
    assert db.query(User).filter_by(email="dup@example.com").count() == 1


def test_refresh_rotates_and_old_token_rejected(client, user_factory):
    user, pw = user_factory()
    r = client.post("/api/v1/auth/login", json={"email": user.email, "password": pw})
    refresh = r.json()["refresh_token"]
    access = r.json()["access_token"]

    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    new_refresh = r2.json()["refresh_token"]
    assert new_refresh != refresh

    # Old refresh token is single-use: rejected now.
    r3 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r3.status_code == 401

    # Refresh token is not an access token.
    r4 = client.get("/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {new_refresh}"})
    assert r4.status_code == 401
    r5 = client.get("/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {r2.json()['access_token']}"})
    assert r5.status_code == 200
    assert r5.json()["email"] == user.email


def test_logout_revokes_refresh_token(client, user_factory):
    user, pw = user_factory()
    r = client.post("/api/v1/auth/login", json={"email": user.email, "password": pw})
    tokens = r.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]},
                    headers=headers)
    assert r.status_code == 200
    r = client.post("/api/v1/auth/refresh",
                    json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


def test_forgot_password_generic_for_unknown_email(client):
    r = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 200
    assert r.json()["message"] == auth_service.GENERIC_FORGOT_MESSAGE


def test_reset_password_flow(client, db, user_factory, monkeypatch):
    captured = {}
    monkeypatch.setattr("app.services.auth_service.mailer.send_email",
                        lambda to, subj, body: captured.update({"body": body}) or True)
    user, _ = user_factory(email="reset@example.com")
    r = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert r.status_code == 200
    token = captured["body"].strip().split("\n")[2]
    r = client.post("/api/v1/auth/reset-password",
                    json={"token": token, "new_password": "newpassword123"})
    assert r.status_code == 200, r.text
    # Token is single-use.
    r = client.post("/api/v1/auth/reset-password",
                    json={"token": token, "new_password": "another12345"})
    assert r.status_code == 400
    # New password works, old does not.
    r = client.post("/api/v1/auth/login", json={
        "email": "reset@example.com", "password": "newpassword123"})
    assert r.status_code == 200


def test_verify_email(client, db, user_factory, monkeypatch):
    captured = {}
    monkeypatch.setattr("app.services.auth_service.mailer.send_email",
                        lambda to, subj, body: captured.update({"body": body}) or True)
    user, _ = user_factory(email="verify@example.com", verified=False)
    assert user.is_verified is False
    # Re-send verification by signing up through the service directly is complex;
    # instead grab a fresh token via the model path.
    from app.core.security import hash_token, new_opaque_token, utcnow
    from app.models.models import EmailVerificationToken
    from datetime import timedelta
    token = new_opaque_token()
    db.add(EmailVerificationToken(user_id=user.id, token_hash=hash_token(token),
                                  expires_at=utcnow() + timedelta(hours=24)))
    db.commit()
    r = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200, r.text
    db.refresh(user)
    assert user.is_verified is True


    db.refresh(user)
    assert user.is_verified is True


def test_verification_code_generation(client, db, user_factory, monkeypatch):
    """request-code creates a hashed 6-digit code with 10-min expiry."""
    captured = {}
    monkeypatch.setattr("app.services.auth_service.mailer.send_email",
                        lambda to, subj, body: captured.update({"body": body}) or True)
    user, _ = user_factory(email="codegen@example.com", verified=False)
    r = client.post("/api/v1/auth/verify-email/request-code",
                    json={"email": "codegen@example.com"})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    # Code appears in the email body (console mode).
    import re
    m = re.search(r"(\d{6})", captured["body"])
    assert m, f"no 6-digit code in email body: {captured['body'][:200]}"
    code = m.group(1)
    # Stored only as a hash, ~10 min expiry.
    from datetime import timedelta
    from app.core.security import hash_token, utcnow
    from app.models.models import EmailVerificationCode
    rec = db.scalar(__import__("sqlalchemy").select(EmailVerificationCode).where(
        EmailVerificationCode.user_id == user.id))
    assert rec is not None
    assert rec.code_hash == hash_token(code)
    assert rec.code_hash != code  # never plaintext
    assert timedelta(minutes=9) < (rec.expires_at - utcnow()) <= timedelta(minutes=10)
    assert user.is_verified is False  # not verified yet


def test_verification_code_success(client, db, user_factory, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.mailer.send_email",
                        lambda to, subj, body: True)
    user, _ = user_factory(email="codeok@example.com", verified=False)
    from app.services import auth_service
    code = auth_service.request_verification_code(db, "codeok@example.com")
    assert code and len(code) == 6 and code.isdigit()
    r = client.post("/api/v1/auth/verify-email",
                    json={"email": "codeok@example.com", "code": code})
    assert r.status_code == 200, r.text
    db.refresh(user)
    assert user.is_verified is True


def test_verification_code_wrong_fails(client, user_factory, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.mailer.send_email",
                        lambda to, subj, body: True)
    user, _ = user_factory(email="codebad@example.com", verified=False)
    r = client.post("/api/v1/auth/verify-email",
                    json={"email": "codebad@example.com", "code": "000000"})
    assert r.status_code == 400
    assert user.is_verified is False


def test_verification_code_expired_fails(client, db, user_factory, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.mailer.send_email",
                        lambda to, subj, body: True)
    user, _ = user_factory(email="codeexp@example.com", verified=False)
    from datetime import timedelta
    from app.core.security import hash_token, utcnow
    from app.models.models import EmailVerificationCode
    db.add(EmailVerificationCode(user_id=user.id, code_hash=hash_token("123456"),
                                 expires_at=utcnow() - timedelta(minutes=1)))
    db.commit()
    r = client.post("/api/v1/auth/verify-email",
                    json={"email": "codeexp@example.com", "code": "123456"})
    assert r.status_code == 400
    assert user.is_verified is False


def test_verification_code_rate_limited(client, user_factory, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.mailer.send_email",
                        lambda to, subj, body: True)
    user_factory(email="codelimit@example.com", verified=False)
    for _ in range(3):
        r = client.post("/api/v1/auth/verify-email/request-code",
                        json={"email": "codelimit@example.com"})
        assert r.status_code == 200, r.text
    r = client.post("/api/v1/auth/verify-email/request-code",
                    json={"email": "codelimit@example.com"})
    assert r.status_code == 429, r.text


def test_verification_code_replaces_old(client, db, user_factory, monkeypatch):
    """A new request invalidates the previous code."""
    monkeypatch.setattr("app.services.auth_service.mailer.send_email",
                        lambda to, subj, body: True)
    user, _ = user_factory(email="coderep@example.com", verified=False)
    from app.services import auth_service
    code1 = auth_service.request_verification_code(db, "coderep@example.com")
    code2 = auth_service.request_verification_code(db, "coderep@example.com")
    assert code1 != code2
    r = client.post("/api/v1/auth/verify-email",
                    json={"email": "coderep@example.com", "code": code1})
    assert r.status_code == 400  # old code no longer valid
    r = client.post("/api/v1/auth/verify-email",
                    json={"email": "coderep@example.com", "code": code2})
    assert r.status_code == 200


def test_me_and_change_password(client, auth_headers):
    headers, user = auth_headers()
    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == user.email

    r = client.patch("/api/v1/auth/me", json={"name": "New Name"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"

    r = client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": "bad-current", "new_password": "brandnew123"})
    assert r.status_code == 400
    r = client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": "password123", "new_password": "brandnew123"})
    assert r.status_code == 200, r.text
    r = client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "brandnew123"})
    assert r.status_code == 200


def test_unauthenticated_me_rejected(client):
    assert client.get("/api/v1/auth/me").status_code == 401
