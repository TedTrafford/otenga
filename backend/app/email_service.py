"""
Email helper for Otenga BI Platform.

Behaviour:
  • If SMTP_HOST is set → sends a real HTML email via STARTTLS (port 587) or
    falls back to SSL (port 465).
  • If SMTP_HOST is empty → prints the verification link to stdout so
    developers can click it during local development.
"""

import smtplib
import logging
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .config import settings

log = logging.getLogger(__name__)

# ── HTML email template ────────────────────────────────────────────────────────

def _build_html(username: str, link: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#030310;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#030310;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0"
        style="background:#0a0a25;border-radius:16px;border:1px solid rgba(0,212,255,0.2);overflow:hidden;max-width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#00D4FF,#7C3AED);padding:28px 36px;">
            <h1 style="margin:0;font-size:22px;font-weight:700;color:#fff;letter-spacing:-0.5px;">
              &#9889; Otenga BI Platform
            </h1>
            <p style="margin:4px 0 0;font-size:11px;color:rgba(255,255,255,0.7);text-transform:uppercase;letter-spacing:2px;">
              Email Verification
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px 36px;">
            <p style="margin:0 0 8px;font-size:15px;color:#e2e8f0;">
              Hi <strong style="color:#00D4FF;">{username}</strong>,
            </p>
            <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;line-height:1.7;">
              Thanks for registering on <strong style="color:#e2e8f0;">Otenga</strong>!
              Click the button below to verify your email address. Once verified your account will be
              reviewed by an administrator before you can sign in.
            </p>

            <!-- CTA Button -->
            <div style="text-align:center;margin:32px 0;">
              <a href="{link}"
                style="display:inline-block;background:linear-gradient(135deg,#00D4FF,#7C3AED);
                       color:#030310;font-weight:700;font-size:14px;text-decoration:none;
                       padding:14px 36px;border-radius:12px;letter-spacing:0.3px;">
                &#9989; Verify My Email Address
              </a>
            </div>

            <!-- Steps -->
            <table width="100%" cellpadding="0" cellspacing="6" style="margin:24px 0;">
              <tr>
                <td style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.15);
                            border-radius:8px;padding:10px 14px;font-size:12px;color:#94a3b8;">
                  <strong style="color:#00D4FF;">1.</strong> Click the button above to verify your email
                </td>
              </tr>
              <tr><td height="6"></td></tr>
              <tr>
                <td style="background:rgba(124,58,237,0.06);border:1px solid rgba(124,58,237,0.15);
                            border-radius:8px;padding:10px 14px;font-size:12px;color:#94a3b8;">
                  <strong style="color:#A78BFA;">2.</strong> Wait for an administrator to approve your account
                </td>
              </tr>
              <tr><td height="6"></td></tr>
              <tr>
                <td style="background:rgba(6,255,165,0.06);border:1px solid rgba(6,255,165,0.15);
                            border-radius:8px;padding:10px 14px;font-size:12px;color:#94a3b8;">
                  <strong style="color:#06FFA5;">3.</strong> Sign in and start using Otenga!
                </td>
              </tr>
            </table>

            <!-- Fallback link -->
            <p style="margin:20px 0 0;font-size:11px;color:#475569;text-align:center;line-height:1.7;">
              Button not working? Copy and paste this link:<br>
              <a href="{link}" style="color:#00D4FF;word-break:break-all;font-size:11px;">{link}</a>
            </p>
            <p style="margin:12px 0 0;font-size:11px;color:#334155;text-align:center;">
              This link expires in <strong style="color:#FFB800;">24 hours</strong>.
              If you didn't register, ignore this email.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:16px 36px 24px;border-top:1px solid rgba(255,255,255,0.05);">
            <p style="margin:0;font-size:11px;color:#334155;text-align:center;">
              &copy; 2026 Otenga &middot; Aleza Credit BI Platform
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Sender ─────────────────────────────────────────────────────────────────────

def send_verification_email(to_email: str, username: str, token: str) -> None:
    """Send (or log) an email verification message."""
    link = f"{settings.APP_BASE_URL}/verify-email?token={token}"

    if not settings.SMTP_HOST:
        _console_fallback(to_email, username, link)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Verify your Otenga account — {username}"
    msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"]      = to_email

    plain = (
        f"Hi {username},\n\n"
        f"Please verify your email address by visiting:\n{link}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"— Otenga BI Platform / Aleza Credit"
    )
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(_build_html(username, link), "html", "utf-8"))

    # Try STARTTLS (port 587) first, fall back to SSL (port 465)
    sent = _try_starttls(msg, to_email) or _try_ssl(msg, to_email)
    if not sent:
        log.warning("All SMTP methods failed; falling back to console output.")
        _console_fallback(to_email, username, link)


def _try_starttls(msg: MIMEMultipart, to_email: str) -> bool:
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as srv:
            srv.ehlo()
            srv.starttls(context=ssl.create_default_context())
            srv.ehlo()
            if settings.SMTP_USER:
                srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            srv.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
        log.info("Verification email sent (STARTTLS) to %s", to_email)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        log.error("SMTP authentication failed: %s", exc)
        print(f"\n[SMTP AUTH ERROR] Check SMTP_USER / SMTP_PASSWORD in backend/.env\n{exc}\n")
        return False
    except Exception as exc:
        log.debug("STARTTLS attempt failed: %s", exc)
        return False


def _try_ssl(msg: MIMEMultipart, to_email: str) -> bool:
    ssl_port = 465
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, ssl_port, context=ctx, timeout=15) as srv:
            if settings.SMTP_USER:
                srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            srv.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
        log.info("Verification email sent (SSL) to %s", to_email)
        return True
    except Exception as exc:
        log.debug("SSL attempt failed: %s", exc)
        return False


def _console_fallback(to_email: str, username: str, link: str) -> None:
    sep = "=" * 72
    print(f"\n{sep}")
    print("[OTENGA] EMAIL VERIFICATION — No SMTP configured (dev mode)")
    print(f"  To      : {to_email}")
    print(f"  User    : {username}")
    print(f"  Link    : {link}")
    print(f"{sep}")
    print("  → Open the link above in your browser to verify the account.")
    print(f"  → Then approve it from the Admin → User Management page.")
    print(f"{sep}\n")
