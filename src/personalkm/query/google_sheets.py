from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


GOOGLE_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


@dataclass(frozen=True, slots=True)
class GoogleOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str


@dataclass(frozen=True, slots=True)
class GoogleSheetExport:
    spreadsheet_id: str
    url: str


def google_oauth_config_from_env() -> GoogleOAuthConfig | None:
    client_id = os.getenv("ASKDANNY_GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("ASKDANNY_GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv(
        "ASKDANNY_GOOGLE_REDIRECT_URI",
        "https://personalkm.onrender.com/oauth/google/callback",
    ).strip()
    if not client_id or not client_secret or not redirect_uri:
        return None
    return GoogleOAuthConfig(client_id, client_secret, redirect_uri)


def google_authorization_url(config: GoogleOAuthConfig, state: str) -> str:
    params = {
        'client_id': config.client_id,
        'redirect_uri': config.redirect_uri,
        'response_type': 'code',
        'scope': GOOGLE_SHEETS_SCOPE,
        'access_type': 'online',
        'prompt': 'select_account',
        'state': state,
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"


async def export_to_google_sheet(
    config: GoogleOAuthConfig,
    code: str,
    rows: list[list[str]],
) -> GoogleSheetExport:
    async with httpx.AsyncClient(timeout=20.0) as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uri": config.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        token_payload = token_response.json()
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Google OAuth response did not include an access token")

        create_response = await client.post(
            GOOGLE_SHEETS_API,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"properties": {"title": "AskDanny 查詢結果"}},
        )
        create_response.raise_for_status()
        spreadsheet_payload = create_response.json()
        spreadsheet_id = spreadsheet_payload.get("spreadsheetId")
        if not isinstance(spreadsheet_id, str) or not spreadsheet_id:
            raise ValueError("Google Sheets response did not include a spreadsheet id")

        row_end = max(len(rows), 1)
        values_response = await client.put(
            f"{GOOGLE_SHEETS_API}/{spreadsheet_id}/values/A1:H{row_end}",
            params={"valueInputOption": "USER_ENTERED"},
            headers={"Authorization": f"Bearer {access_token}"},
            json={"majorDimension": "ROWS", "values": rows},
        )
        values_response.raise_for_status()

    return GoogleSheetExport(
        spreadsheet_id=spreadsheet_id,
        url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
    )
