"""Multi-channel dispatch: SendGrid, LinkedIn, WhatsApp"""
from __future__ import annotations
import logging
import json
from typing import Any
import httpx
from app.core.settings import settings

log = logging.getLogger(__name__)

COUNTRY_TZ = {
    "germany":"Europe/Berlin","france":"Europe/Paris","india":"Asia/Kolkata",
    "usa":"America/New_York","uk":"Europe/London","japan":"Asia/Tokyo",
}

OPTIMAL_HOURS = range(9, 12)  # 9am–11am local


class DispatchService:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def send(self, channel: str, email: str, name: str,
                   subject: str, body: str, metadata: dict = None) -> bool:
        if channel == "email":
            return await self._sendgrid(email, name, subject, body, metadata or {})
        elif channel == "linkedin":
            return await self._linkedin(metadata.get("linkedin_url",""), body)
        elif channel == "whatsapp":
            return await self._whatsapp(metadata.get("phone",""), body)
        return False

    async def _sendgrid(self, to_email: str, to_name: str, subject: str,
                        body: str, metadata: dict) -> bool:
        if not settings.SENDGRID_API_KEY:
            log.info("SENDGRID not configured — simulating send to %s", to_email[:4] + "***")
            return True  # simulate success in dev

        html = self._html_wrap(body, to_name)
        payload = {
            "personalizations": [{"to": [{"email": to_email, "name": to_name}], "subject": subject,
                                   "custom_args": {k: str(v) for k, v in metadata.items()}}],
            "from": {"email": settings.SENDGRID_FROM_EMAIL, "name": settings.SENDGRID_FROM_NAME},
            "content": [{"type": "text/html", "value": html}],
            "tracking_settings": {"click_tracking": {"enable": True}, "open_tracking": {"enable": True}},
            "mail_settings": {"sandbox_mode": {"enable": settings.ENVIRONMENT != "production"}},
        }
        try:
            resp = await self.http.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code in (200, 202):
                log.info("Email sent to %s***", to_email[:4])
                return True
            log.error("SendGrid error %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            log.error("SendGrid request failed: %s", e)
        return False

    async def _linkedin(self, linkedin_url: str, body: str) -> bool:
        if not settings.LINKEDIN_ACCESS_TOKEN or not linkedin_url:
            log.info("LinkedIn not configured or no URL — simulating")
            return True
        try:
            resp = await self.http.post(
                "https://api.linkedin.com/v2/messages",
                headers={"Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
                         "Content-Type": "application/json",
                         "X-Restli-Protocol-Version": "2.0.0"},
                json={"recipients": [{"person": {"$URN": linkedin_url}}], "subject": "", "body": body[:2000]},
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            log.error("LinkedIn dispatch failed: %s", e)
        return False

    async def _whatsapp(self, phone: str, body: str) -> bool:
        if not settings.WHATSAPP_API_TOKEN or not phone:
            log.info("WhatsApp not configured or no phone — simulating")
            return True
        try:
            resp = await self.http.post(
                f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers={"Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}", "Content-Type": "application/json"},
                json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": body[:4096]}},
            )
            return resp.status_code == 200
        except Exception as e:
            log.error("WhatsApp dispatch failed: %s", e)
        return False

    @staticmethod
    def _html_wrap(body: str, name: str) -> str:
        html_body = body.replace("\n", "<br>")
        return f"""<!doctype html><html><head><meta charset="utf-8">
<style>body{{font-family:'Helvetica Neue',Arial,sans-serif;font-size:15px;color:#222;line-height:1.7;background:#f7f7f5;margin:0;padding:24px}}
.w{{max-width:580px;margin:0 auto;background:#fff;padding:32px;border-radius:8px;border:1px solid #e0e0e0}}
.f{{font-size:12px;color:#999;margin-top:28px;border-top:1px solid #f0f0f0;padding-top:16px}}
a{{color:#1B6B3A}}</style></head>
<body><div class="w">{html_body}
<div class="f">Treeni Sustainability Solutions · <a href="{{{{unsubscribe}}}}">Unsubscribe</a></div>
</div></body></html>"""
