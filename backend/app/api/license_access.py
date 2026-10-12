"""Gumroad buyer access: license verification + gated APK download.

Public buyer flow (no login needed):
  POST /api/v1/gumroad/licenses/verify   {product_permalink, license_key}
    -> {verified, product_name, download_token, download_url}
  GET  /api/v1/gumroad/apk/download?token=<download_token>
    -> the APK file, only after a FRESH Gumroad re-verification.

Seller setup (Anna only):
  GET  /gumroad-setup   (HTML form over HTTPS)
  POST /api/v1/gumroad-accounts/oauth/app-credentials
    {email, password, client_id, client_secret}
    -> stores the Gumroad app credentials in the server .env (never in chat,
       never in the app, never in logs).
  GET  /api/v1/gumroad-accounts/oauth/config-status  (login required)
    -> {client_id_configured, redirect_uri} — the exact URI to paste into Gumroad.

Nothing here ever returns a Gumroad token/secret or a raw license key.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import check_rate_limit, get_current_user, get_db
from app.core.security import (
    create_license_download_token,
    decode_license_download_token,
)
from app.gumroad.exceptions import GumroadError
from app.models.models import LicenseGrant, User
from app.services import auth_service, license_service

log = logging.getLogger("license_access")

router = APIRouter(prefix="/api/v1", tags=["gumroad-buyer-access"])
pages_router = APIRouter(tags=["gumroad-setup"])

CALLBACK_PATH = "/api/v1/gumroad-accounts/oauth/callback"
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


# ---------------------------------------------------------------- helpers

def public_base_url(request: Request | None = None) -> str:
    """Current public HTTPS base URL of this backend.

    Prefers the watchdog-maintained PUBLIC_URL.txt (the canonical public URL),
    falls back to the incoming request's base URL.
    """
    url_file = os.path.join(os.path.dirname(ENV_PATH), "PUBLIC_URL.txt")
    try:
        with open(url_file, "r", encoding="utf-8") as fh:
            url = fh.read().strip().strip("/")
            if url.startswith("http"):
                return url
    except OSError:
        pass
    if request is not None:
        return str(request.base_url).rstrip("/")
    return ""


def redirect_uri(request: Request | None = None) -> str:
    """Exact OAuth redirect URI to register in the Gumroad app settings."""
    configured = (get_settings().GUMROAD_REDIRECT_URI or "").strip().rstrip("/")
    if configured:
        return configured
    base = public_base_url(request)
    return f"{base}{CALLBACK_PATH}" if base else ""


def _write_env_vars(updates: dict[str, str]) -> None:
    """Upsert KEY=VALUE lines in backend/.env (file is chmod 600)."""
    lines: list[str] = []
    seen: set[str] = set()
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    with open(ENV_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    os.environ.update(updates)
    get_settings.cache_clear()


# ---------------------------------------------------------------- schemas

class VerifyIn(BaseModel):
    product_permalink: str = Field(min_length=2, max_length=500)
    license_key: str = Field(min_length=4, max_length=200)


class AppCredentialsIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)
    client_id: str = Field(min_length=4, max_length=200)
    client_secret: str = Field(min_length=4, max_length=200)


# ------------------------------------------------------- buyer: verify ---

@router.post("/gumroad/licenses/verify")
def verify_license(body: VerifyIn, request: Request, db: Session = Depends(get_db)):
    """Verify a buyer's Gumroad license key. Returns a download token on success."""
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"license-verify:{ip}", 20, 3600)
    try:
        ok, reason, grant = license_service.verify_and_grant(
            db, body.product_permalink.strip(), body.license_key.strip())
    except GumroadError:
        # Gumroad unreachable -> fail closed, no grant.
        raise HTTPException(status_code=503,
                            detail="License service is temporarily unavailable. Try again later.")
    if not ok or grant is None:
        raise HTTPException(status_code=403, detail=f"License not valid: {reason}")
    settings = get_settings()
    token = create_license_download_token(grant.id, settings.SECRET_KEY,
                                          settings.LICENSE_DOWNLOAD_MINUTES)
    base = public_base_url(request)
    return {
        "verified": True,
        "product_name": grant.product_name,
        "download_token": token,
        "download_url": f"{base}/api/v1/gumroad/apk/download?token={token}",
    }


# ------------------------------------------------------- buyer: download --

@router.get("/gumroad/apk/download")
def download_apk(token: str = Query(min_length=10), db: Session = Depends(get_db)):
    """Serve the APK only to a buyer whose license re-verifies with Gumroad NOW.

    Every download triggers a fresh license check, so refunded / revoked /
    disputed purchases are denied immediately.
    """
    settings = get_settings()
    payload = decode_license_download_token(token, settings.SECRET_KEY)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired download token")
    grant = db.get(LicenseGrant, payload.get("sub"))
    if grant is None or grant.status != "active":
        raise HTTPException(status_code=403, detail="No active license for this download")
    try:
        ok, reason = license_service.recheck_grant(db, grant)
    except GumroadError:
        raise HTTPException(status_code=503,
                            detail="License service is temporarily unavailable. Try again later.")
    if not ok:
        raise HTTPException(status_code=403, detail=f"License no longer valid: {reason}")
    apk_path = (settings.APK_DOWNLOAD_PATH or "").strip()
    if not apk_path or not os.path.isfile(apk_path):
        log.error("APK_DOWNLOAD_PATH is not configured or file missing")
        raise HTTPException(status_code=503, detail="Download is not configured on the server.")
    return FileResponse(apk_path, media_type="application/vnd.android.package-archive",
                        filename="gumroad-automation.apk")


# ------------------------------------------------------- seller: setup ----

@router.get("/gumroad-accounts/oauth/config-status")
def oauth_config_status(request: Request, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """What Anna needs to paste into her Gumroad app ('Angel') settings."""
    settings = get_settings()
    return {
        "client_id_configured": bool(settings.GUMROAD_CLIENT_ID),
        "client_secret_configured": bool(settings.GUMROAD_CLIENT_SECRET),
        "redirect_uri": redirect_uri(request),
        "authorize_url": settings.GUMROAD_AUTHORIZE_URL,
    }


@router.post("/gumroad-accounts/oauth/app-credentials")
def save_app_credentials(body: AppCredentialsIn, request: Request,
                         db: Session = Depends(get_db)):
    """Store the Gumroad Application ID + Secret in the server .env.

    Authenticated with Anna's backend email+password (never in chat).
    Values are never logged and never returned.
    """
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"app-credentials:{ip}", 10, 3600)
    user = auth_service.authenticate(db, body.email.strip(), body.password)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Backend email or password is incorrect.")
    _write_env_vars({
        "GUMROAD_CLIENT_ID": body.client_id.strip(),
        "GUMROAD_CLIENT_SECRET": body.client_secret.strip(),
    })
    log.info("gumroad app credentials saved by user=%s", user.email)
    return {"ok": True, "redirect_uri": redirect_uri(request)}


SETUP_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Connect Gumroad App</title>
<style>
body{font-family:system-ui,sans-serif;max-width:480px;margin:40px auto;padding:0 16px;color:#1a1a2e}
h1{font-size:22px}.card{border:1px solid #ddd;border-radius:12px;padding:20px}
label{display:block;margin:12px 0 4px;font-weight:600}input{width:100%;padding:10px;border:1px solid #bbb;border-radius:8px;box-sizing:border-box}
button{margin-top:16px;width:100%;padding:12px;background:#4f46e5;color:#fff;border:0;border-radius:8px;font-size:16px}
#msg{margin-top:12px;font-weight:600}.ok{color:green}.err{color:#b00020}
.small{font-size:13px;color:#555;margin-top:12px}
code{background:#f3f3f3;padding:2px 6px;border-radius:4px;word-break:break-all}
</style></head>
<body>
<h1>Connect your Gumroad app</h1>
<div class="card">
<p class="small">Enter your <b>backend</b> login plus the <b>Application ID</b> and
<b>Application Secret</b> from your Gumroad Developer Application. They are stored
only on this server — never shown again.</p>
<form id="f">
<label>Backend email</label><input id="email" type="email" required autocomplete="username">
<label>Backend password</label><input id="password" type="password" required autocomplete="current-password">
<label>Gumroad Application ID</label><input id="client_id" required autocomplete="off">
<label>Gumroad Application Secret</label><input id="client_secret" type="password" required autocomplete="off">
<button type="submit">Save securely</button>
</form>
<div id="msg"></div>
<p class="small">After saving, open your Gumroad app settings and set the
<b>Redirect URI</b> to:<br><code id="ru"></code></p>
</div>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('msg');
  msg.className = ''; msg.textContent = 'Saving...';
  const body = {
    email: document.getElementById('email').value,
    password: document.getElementById('password').value,
    client_id: document.getElementById('client_id').value.trim(),
    client_secret: document.getElementById('client_secret').value.trim(),
  };
  try {
    const r = await fetch('/api/v1/gumroad-accounts/oauth/app-credentials', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)});
    const j = await r.json();
    if (r.ok && j.ok) {
      msg.className = 'ok';
      msg.textContent = 'Saved. Now set this Redirect URI in your Gumroad app: ' + j.redirect_uri;
      document.getElementById('ru').textContent = j.redirect_uri;
      document.getElementById('client_secret').value = '';
      document.getElementById('password').value = '';
    } else {
      msg.className = 'err';
      msg.textContent = 'Error: ' + (j.detail || r.status);
    }
  } catch (err) {
    msg.className = 'err'; msg.textContent = 'Network error: ' + err;
  }
});
</script>
</body></html>
"""


@pages_router.get("/gumroad-setup", response_class=HTMLResponse)
def gumroad_setup_page():
    """Secure HTTPS form for Anna to paste her Gumroad app credentials (no chat)."""
    return SETUP_HTML


@pages_router.get("/app-setup", response_class=HTMLResponse)
def app_setup_page():
    """Shows the current backend URL with a copy button for the Android app settings.

    The tunnel URL rotates, so this page reads PUBLIC_URL.txt live — always fresh.
    """
    from pathlib import Path
    try:
        public_url = Path(__file__).resolve().parent.parent.parent.joinpath(
            "PUBLIC_URL.txt").read_text().strip()
    except OSError:
        public_url = ""
    api_url = f"{public_url}/api/v1" if public_url else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>App Setup — Backend URL</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:480px;margin:40px auto;padding:0 16px;color:#1a1a2e}}
.card{{border:1px solid #ddd;border-radius:12px;padding:20px}}
code{{display:block;background:#f3f3f3;padding:12px;border-radius:8px;word-break:break-all;font-size:14px;margin:12px 0}}
button{{width:100%;padding:12px;background:#4f46e5;color:#fff;border:0;border-radius:8px;font-size:16px}}
#msg{{margin-top:12px;font-weight:600;color:green}}
.small{{font-size:13px;color:#555;margin-top:12px}}
</style></head>
<body>
<h1>Backend URL for the app</h1>
<div class="card">
<p class="small">Copy this URL, then in the app go to <b>Settings → Backend base URL</b>, paste it and tap <b>Save</b>.</p>
<code id="url">{api_url or "URL not available — backend starting, refresh in a minute."}</code>
<button onclick="navigator.clipboard.writeText(document.getElementById('url').textContent).then(()=>{{document.getElementById('msg').textContent='Copied!'}})">Copy URL</button>
<div id="msg"></div>
<p class="small">This URL changes from time to time. If the app says "No connection to the backend", open this page again and copy the fresh URL.</p>
</div>
</body></html>"""


# ------------------------------------------------ GitHub PAT + gist setup
# Lets Anna paste a GitHub fine-grained PAT (Gists read/write) over HTTPS.
# The backend validates it, stores it in .env, creates a PUBLIC gist holding
# the current tunnel URL, and the watchdog keeps that gist fresh on rotation.
# The Android app reads the gist's raw URL to auto-update its backend URL.

class GithubPatIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)
    pat: str = Field(min_length=10, max_length=500)


def _github_api(pat: str):
    from app.gumroad.http import gumroad_http_client
    return gumroad_http_client(), {"Authorization": f"Bearer {pat.strip()}",
                                   "Accept": "application/vnd.github+json"}


@router.post("/admin/github-pat")
def save_github_pat(body: GithubPatIn, request: Request,
                    db: Session = Depends(get_db)):
    """Validate Anna's GitHub PAT, store it, and create the public URL gist.

    Authenticated with Anna's backend email+password (never in chat).
    The PAT is never logged and never returned.
    """
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"github-pat:{ip}", 10, 3600)
    user = auth_service.authenticate(db, body.email.strip(), body.password)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Backend email or password is incorrect.")
    pat = body.pat.strip()
    client, headers = _github_api(pat)
    try:
        r = client.get("https://api.github.com/user", headers=headers)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GitHub unreachable: {exc}")
    if r.status_code != 200:
        raise HTTPException(status_code=400,
                            detail="GitHub token invalid. Fine-grained PAT with Gists read/write chahiye.")
    # Create (or reuse) the public gist holding the backend URL.
    try:
        public_url = Path(__file__).resolve().parent.parent.parent.joinpath(
            "PUBLIC_URL.txt").read_text().strip()
    except OSError:
        public_url = ""
    gist_id = os.environ.get("GIST_ID", "")
    if gist_id:
        gr = client.patch(f"https://api.github.com/gists/{gist_id}", headers=headers,
                          json={"files": {"backend-url.txt": {"content": public_url}}})
    else:
        gr = client.post("https://api.github.com/gists", headers=headers,
                         json={"description": "Gumroad Automation backend URL (auto-updated)",
                               "public": True,
                               "files": {"backend-url.txt": {"content": public_url}}})
    if gr.status_code not in (200, 201):
        raise HTTPException(status_code=502,
                            detail="Gist create/update failed. Token me Gists permission check karo.")
    gist_id = gr.json()["id"]
    raw_url = f"https://gist.githubusercontent.com/{gr.json()['owner']['login']}/{gist_id}/raw/backend-url.txt"
    _write_env_vars({"GITHUB_PAT": pat, "GIST_ID": gist_id, "GIST_RAW_URL": raw_url})
    log.info("github PAT + gist saved by user=%s gist=%s", user.email, gist_id)
    return {"ok": True, "gist_id": gist_id, "raw_url": raw_url}


GITHUB_SETUP_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auto-Update Setup</title>
<style>
body{font-family:system-ui,sans-serif;max-width:480px;margin:40px auto;padding:0 16px;color:#1a1a2e}
h1{font-size:22px}.card{border:1px solid #ddd;border-radius:12px;padding:20px}
label{display:block;margin:12px 0 4px;font-weight:600}input{width:100%;padding:10px;border:1px solid #bbb;border-radius:8px;box-sizing:border-box}
button{margin-top:16px;width:100%;padding:12px;background:#4f46e5;color:#fff;border:0;border-radius:8px;font-size:16px}
#msg{margin-top:12px;font-weight:600}.ok{color:green}.err{color:#b00020}
.small{font-size:13px;color:#555;margin-top:12px}
ol.small li{margin-bottom:8px}
</style></head>
<body>
<h1>Auto-update setup (ek dafa)</h1>
<div class="card">
<p class="small">Iske baad app khud naya backend URL utha legi — tumhe kuch nahi karna padega.</p>
<ol class="small">
<li><a href="https://github.com/settings/tokens?type=beta" target="_blank">Yahan</a> se <b>fine-grained PAT</b> banao (expiry 30 din), sirf <b>Gists → Read and write</b> permission do.</li>
<li>Neeche apna <b>backend login</b> aur wo token paste karo.</li>
</ol>
<form id="f">
<label>Backend email</label><input id="email" type="email" required autocomplete="username">
<label>Backend password</label><input id="password" type="password" required autocomplete="current-password">
<label>GitHub token (PAT)</label><input id="pat" type="password" required autocomplete="off" placeholder="github_pat_...">
<button type="submit">Save securely</button>
</form>
<div id="msg"></div>
</div>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('msg');
  msg.className = ''; msg.textContent = 'Saving...';
  const body = {
    email: document.getElementById('email').value.trim(),
    password: document.getElementById('password').value,
    pat: document.getElementById('pat').value.trim(),
  };
  try {
    const r = await fetch('/api/v1/admin/github-pat', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)});
    const j = await r.json();
    if (r.ok && j.ok) {
      msg.className = 'ok';
      msg.textContent = 'Ho gaya! Ab nayi APK install karo — uske baad URL khud update hoga.';
      document.getElementById('pat').value = '';
      document.getElementById('password').value = '';
    } else {
      msg.className = 'err';
      msg.textContent = 'Error: ' + (j.detail || r.status);
    }
  } catch (err) {
    msg.className = 'err'; msg.textContent = 'Network error: ' + err;
  }
});
</script>
</body></html>
"""


@pages_router.get("/github-setup", response_class=HTMLResponse)
def github_setup_page():
    """Secure HTTPS form for Anna to paste her GitHub PAT (no chat)."""
    return GITHUB_SETUP_HTML


SMTP_SETUP_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Email Setup</title>
<style>body{font-family:system-ui;max-width:420px;margin:2em auto;padding:0 1em}
input{width:100%;padding:10px;margin:6px 0;box-sizing:border-box}
button{background:#1a73e8;color:#fff;border:0;padding:12px;width:100%;font-size:16px;border-radius:6px}
.ok{color:green}.err{color:red}</style></head><body>
<h2>Email Setup</h2>
<p>Enter your Gmail + App Password to enable verification codes via email.<br>
<small>Get an App Password: Google Account → Security → 2-Step Verification → App passwords.</small></p>
<input id="email" type="email" placeholder="Backend email">
<input id="password" type="password" placeholder="Backend password">
<input id="smtp_user" type="email" placeholder="Gmail address">
<input id="smtp_pass" type="password" placeholder="Gmail App Password">
<button id="save">Save securely</button>
<p id="msg"></p>
<script>
document.getElementById('save').onclick = async () => {
  const msg = document.getElementById('msg');
  const body = {
    email: document.getElementById('email').value,
    password: document.getElementById('password').value,
    smtp_user: document.getElementById('smtp_user').value,
    smtp_password: document.getElementById('smtp_pass').value,
  };
  try {
    const r = await fetch('/api/v1/admin/smtp', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)});
    const j = await r.json();
    if (r.ok) { msg.className = 'ok'; msg.textContent = 'Saved! Email verification codes will now be sent.'; }
    else { msg.className = 'err'; msg.textContent = 'Error: ' + (j.detail || r.status); }
  } catch (err) { msg.className = 'err'; msg.textContent = 'Network error'; }
};
</script></body></html>"""


@pages_router.get("/smtp-setup", response_class=HTMLResponse)
def smtp_setup_page():
    """Secure HTTPS form for Anna to save Gmail SMTP credentials (no chat)."""
    return SMTP_SETUP_HTML


class SmtpIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)
    smtp_user: str = Field(min_length=3, max_length=320)
    smtp_password: str = Field(min_length=1, max_length=200)


@router.post("/admin/smtp")
def save_smtp(body: SmtpIn, request: Request, db: Session = Depends(get_db)):
    """Save Anna's Gmail SMTP credentials for sending verification codes.

    Authenticated with Anna's backend email+password (never in chat).
    The SMTP password is never logged and never returned.
    """
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"smtp:{ip}", 10, 3600)
    user = auth_service.authenticate(db, body.email.strip(), body.password)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Backend email or password is incorrect.")
    _set_env_kv({
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": body.smtp_user.strip(),
        "SMTP_PASSWORD": body.smtp_password.strip(),
        "MAIL_MODE": "smtp",
        "MAIL_FROM": body.smtp_user.strip(),
    })
    return {"ok": True}
