import httpx

API = "https://api.telegram.org/bot{token}/{method}"


def send_message(token: str, chat_id: str, html: str) -> None:
    resp = httpx.post(
        API.format(token=token, method="sendMessage"),
        json={"chat_id": chat_id, "text": html, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=20,
    )
    resp.raise_for_status()


def find_chat_ids(token: str) -> list[tuple[str, str]]:
    """Chats that have messaged the bot: send it any message first."""
    resp = httpx.get(API.format(token=token, method="getUpdates"), timeout=20)
    resp.raise_for_status()
    seen = {}
    for upd in resp.json().get("result", []):
        chat = (upd.get("message") or {}).get("chat")
        if chat:
            seen[str(chat["id"])] = chat.get("username") or chat.get("title") or chat.get("first_name", "")
    return list(seen.items())
