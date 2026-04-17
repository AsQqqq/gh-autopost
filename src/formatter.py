from datetime import datetime
from zoneinfo import ZoneInfo

_MOSCOW = ZoneInfo("Europe/Moscow")

# Conventional commit prefixes → emoji label
_COMMIT_TYPES: dict[str, str] = {
    "feat":     "✨ Feature",
    "fix":      "🐛 Fix",
    "docs":     "📚 Docs",
    "style":    "💄 Style",
    "refactor": "♻️ Refactor",
    "perf":     "⚡ Perf",
    "test":     "🧪 Test",
    "build":    "📦 Build",
    "ci":       "👷 CI",
    "chore":    "🔧 Chore",
    "revert":   "⏪ Revert",
}


def classify_commit(message: str) -> str:
    lower = message.lower().strip()
    for prefix, label in _COMMIT_TYPES.items():
        if lower.startswith(f"{prefix}:") or lower.startswith(f"{prefix}("):
            return label
    return "📌 Commit"


def is_merge_commit(message: str) -> bool:
    msg = message.strip()
    return (
        msg.startswith("Merge ")
        or msg.startswith("Merged ")
        or msg.lower().startswith("merge pull request")
    )


def _fmt_date(iso: str) -> str:
    """Convert ISO-8601 string to Moscow time, human-readable."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        msk = dt.astimezone(_MOSCOW)
        return msk.strftime("%d.%m.%Y %H:%M:%S МСК")
    except Exception:
        return iso


def _short_sha(sha: str) -> str:
    return sha[:8]


def _repo_name(repo: str) -> str:
    return repo.split("/")[-1] if "/" in repo else repo


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def format_commit_message(repo: str, branch: str, detail: dict, signature: str) -> str:
    commit = detail.get("commit", {})
    author_info = commit.get("author", {})
    stats = detail.get("stats", {})
    files = detail.get("files", [])

    sha = detail.get("sha", "")
    message = commit.get("message", "").strip()
    author_name = author_info.get("name", "Unknown")
    date_str = _fmt_date(author_info.get("date", ""))
    html_url = detail.get("html_url", "")

    additions = stats.get("additions", 0)
    deletions = stats.get("deletions", 0)
    files_count = len(files)

    commit_type = classify_commit(message)
    # Only first line for subject; preserve rest as body
    subject, _, body = message.partition("\n")
    subject = _truncate(subject.strip(), 200)
    body = _truncate(body.strip(), 500) if body.strip() else ""

    text = (
        f"🔔 *Новый коммит*\n\n"
        f"📦 *Репо:* `{_repo_name(repo)}`\n"
        f"🌿 *Ветка:* `{branch}`\n"
        f"{commit_type}\n"
        f"👤 *Автор:* {author_name}\n"
        f"📅 *Дата:* {date_str}\n\n"
        f"💬 *{subject}*"
    )
    if body:
        text += f"\n\n{body}"

    text += (
        f"\n\n📊 *Статистика:*\n"
        f"• Файлов изменено: {files_count}\n"
        f"• Добавлено: `+{additions}`\n"
        f"• Удалено: `-{deletions}`\n\n"
        f"🔗 [Открыть коммит]({html_url}) — `{_short_sha(sha)}`\n\n"
        f"{signature}"
    )
    return text


def format_batch_message(repo: str, branch: str, commits: list[dict], signature: str) -> str:
    """Single message for multiple commits (lightweight, no per-commit details call)."""
    lines = [
        f"🔔 *{len(commits)} новых коммита*\n",
        f"📦 `{_repo_name(repo)}` · 🌿 `{branch}`\n",
    ]
    for c in commits:
        commit = c.get("commit", {})
        sha = c.get("sha", "")
        html_url = c.get("html_url", "")
        message = commit.get("message", "").strip()
        subject = _truncate(message.split("\n")[0], 120)
        author = commit.get("author", {}).get("name", "?")
        ctype = classify_commit(message)
        lines.append(f"• {ctype} `{_short_sha(sha)}` — [{subject}]({html_url}) _({author})_")

    lines.append(f"\n{signature}")
    return "\n".join(lines)


def format_admin_notification(repo: str, branch: str, author: str, sha: str) -> str:
    return (
        f"📢 Опубликован новый коммит\n"
        f"📦 Репо: `{_repo_name(repo)}`\n"
        f"🌿 Ветка: `{branch}`\n"
        f"👤 Автор: {author}\n"
        f"🔑 SHA: `{_short_sha(sha)}`"
    )
