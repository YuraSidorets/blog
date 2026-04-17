from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path


QUEUE_FIELD_NAMES = {"publish_at", "publish_on", "post_slug"}


@dataclass
class QueuedPost:
    source_path: Path
    publish_at_utc: datetime
    destination_path: Path
    rewritten_content: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish queued markdown files into Jekyll _posts."
    )
    parser.add_argument(
        "--queue-dir",
        default="tools/post-queue/pending",
        help="Folder containing queued markdown files.",
    )
    parser.add_argument(
        "--posts-dir",
        default="_posts",
        help="Destination Jekyll posts folder.",
    )
    parser.add_argument(
        "--now",
        help="Override current UTC time with an ISO-8601 timestamp.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be published without moving files.",
    )
    args = parser.parse_args()

    queue_dir = Path(args.queue_dir)
    posts_dir = Path(args.posts_dir)
    now_utc = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)

    if not queue_dir.exists():
        print(f"Queue directory '{queue_dir}' does not exist. Nothing to publish.")
        return 0

    queued_posts = collect_due_posts(queue_dir, posts_dir, now_utc)
    if not queued_posts:
        print("No queued posts are due for publication.")
        return 0

    print(f"Found {len(queued_posts)} queued post(s) due for publication.")
    for queued_post in queued_posts:
        print(f"- {queued_post.source_path} -> {queued_post.destination_path}")

    if args.dry_run:
        print("Dry run complete. No files were moved.")
        return 0

    posts_dir.mkdir(parents=True, exist_ok=True)

    for queued_post in queued_posts:
        queued_post.source_path.write_text(queued_post.rewritten_content, encoding="utf-8")
        shutil.move(str(queued_post.source_path), str(queued_post.destination_path))

    print(f"Published {len(queued_posts)} queued post(s).")
    return 0


def collect_due_posts(queue_dir: Path, posts_dir: Path, now_utc: datetime) -> list[QueuedPost]:
    queued_posts: list[QueuedPost] = []

    for source_path in sorted(queue_dir.rglob("*.md")):
        if source_path.name.startswith("."):
            continue

        text = source_path.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(text, source_path)

        publish_at_utc = resolve_publish_at(frontmatter, now_utc)
        if publish_at_utc > now_utc:
            continue

        slug = resolve_slug(source_path, frontmatter)
        publish_date = publish_at_utc.date().isoformat()
        destination_filename = f"{publish_date}-{slug}.md"
        destination_path = posts_dir / destination_filename

        if destination_path.exists():
            raise RuntimeError(
                f"Refusing to publish '{source_path}'. Destination '{destination_path}' already exists."
            )

        cleaned_frontmatter = strip_queue_only_fields(frontmatter)
        if not has_top_level_field(cleaned_frontmatter, "date"):
            cleaned_frontmatter = append_field(
                cleaned_frontmatter,
                "date",
                quote_scalar(format_publish_date(publish_at_utc)),
            )

        rewritten_content = join_frontmatter(cleaned_frontmatter, body)
        queued_posts.append(
            QueuedPost(
                source_path=source_path,
                publish_at_utc=publish_at_utc,
                destination_path=destination_path,
                rewritten_content=rewritten_content,
            )
        )

    return sorted(
        queued_posts,
        key=lambda item: (item.publish_at_utc, item.source_path.as_posix().lower()),
    )


def split_frontmatter(text: str, source_path: Path) -> tuple[str, str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise RuntimeError(f"Queued post '{source_path}' must start with YAML frontmatter.")

    parts = normalized.split("\n---\n", 1)
    if len(parts) != 2:
        raise RuntimeError(f"Queued post '{source_path}' is missing a closing frontmatter delimiter.")

    frontmatter = parts[0][4:]
    body = parts[1]
    return frontmatter, body


def join_frontmatter(frontmatter: str, body: str) -> str:
    trimmed_frontmatter = frontmatter.strip("\n")
    normalized_body = body.lstrip("\n")
    if normalized_body:
        return f"---\n{trimmed_frontmatter}\n---\n\n{normalized_body}"
    return f"---\n{trimmed_frontmatter}\n---\n"


def resolve_publish_at(frontmatter: str, now_utc: datetime) -> datetime:
    publish_at_value = extract_top_level_field(frontmatter, "publish_at")
    if publish_at_value:
        return parse_timestamp(unquote_scalar(publish_at_value))

    publish_on_value = extract_top_level_field(frontmatter, "publish_on")
    if publish_on_value:
        publish_date = date.fromisoformat(unquote_scalar(publish_on_value))
        return datetime.combine(publish_date, time.min, tzinfo=timezone.utc)

    return now_utc


def resolve_slug(source_path: Path, frontmatter: str) -> str:
    explicit_slug = extract_top_level_field(frontmatter, "post_slug")
    source_slug = unquote_scalar(explicit_slug) if explicit_slug else source_path.stem
    source_slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", source_slug)
    slug = slugify(source_slug)
    if not slug:
        raise RuntimeError(
            f"Queued post '{source_path}' needs a latin-friendly filename or an explicit post_slug."
        )
    return slug


def slugify(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^\w-]", "-", slug, flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-_")


def extract_top_level_field(frontmatter: str, field_name: str) -> str | None:
    pattern = re.compile(rf"(?m)^{re.escape(field_name)}:\s*(.+?)\s*$")
    match = pattern.search(frontmatter)
    return match.group(1) if match else None


def has_top_level_field(frontmatter: str, field_name: str) -> bool:
    return extract_top_level_field(frontmatter, field_name) is not None


def strip_queue_only_fields(frontmatter: str) -> str:
    retained_lines: list[str] = []
    for line in frontmatter.splitlines():
        if is_queue_only_field(line):
            continue
        retained_lines.append(line)
    return "\n".join(retained_lines).strip("\n")


def is_queue_only_field(line: str) -> bool:
    key_match = re.match(r"^([A-Za-z0-9_-]+):\s*", line)
    return bool(key_match and key_match.group(1) in QUEUE_FIELD_NAMES)


def append_field(frontmatter: str, field_name: str, field_value: str) -> str:
    if frontmatter:
        return f"{frontmatter}\n{field_name}: {field_value}"
    return f"{field_name}: {field_value}"


def parse_timestamp(raw_value: str) -> datetime:
    value = raw_value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed_date = date.fromisoformat(value)
        parsed = datetime.combine(parsed_date, time.min)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_publish_date(publish_at_utc: datetime) -> str:
    return publish_at_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def unquote_scalar(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


def quote_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - script entry point
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
