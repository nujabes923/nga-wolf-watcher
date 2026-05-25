from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SYMBOL_PATTERN = re.compile(r"(?<!\d)[036]\d{5}(?!\d)")
CHINESE_STOCK_HINT = re.compile(r"[\u4e00-\u9fff]{2,8}")

TOPIC_KEYWORDS = {
    "AI": ["AI", "人工智能", "大模型", "算力", "服务器"],
    "CPO": ["CPO", "光模块", "光通信"],
    "机器人": ["机器人", "减速器", "执行器"],
    "半导体": ["半导体", "芯片", "先进封装", "存储"],
    "新能源": ["新能源", "锂电", "光伏", "储能"],
    "券商": ["券商", "证券", "金融"],
    "消费": ["消费", "白酒", "食品", "医药"],
    "指数": ["指数", "大盘", "创业板", "沪指", "深成指"],
}

VIEW_RULES = {
    "risk": ["风险", "小心", "谨慎", "退潮", "分歧", "杀", "跌", "别追"],
    "bullish": ["看好", "机会", "主线", "加强", "突破", "继续", "修复", "走强"],
    "bearish": ["看空", "不看好", "弱", "兑现", "退", "破位"],
    "watch": ["观察", "看看", "等", "关注", "留意"],
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def parse_time(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = text.replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return dt.datetime.strptime(normalized, fmt).isoformat(sep=" ")
        except ValueError:
            pass
    try:
        return dt.datetime.fromisoformat(normalized).isoformat(sep=" ")
    except ValueError:
        return text


def month_key(post_time: str) -> str:
    match = re.match(r"(\d{4})[-/](\d{2})", str(post_time or ""))
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return "unknown-month"


def extract_symbols(text: str) -> list[str]:
    candidates = set(SYMBOL_PATTERN.findall(text or ""))
    return sorted(candidates)


def extract_topics(text: str) -> list[str]:
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword.lower() in (text or "").lower() for keyword in keywords):
            topics.append(topic)
    return topics


def classify_view(text: str) -> str:
    lower = str(text or "").lower()
    scores = {}
    for view, keywords in VIEW_RULES.items():
        scores[view] = sum(1 for keyword in keywords if keyword.lower() in lower)
    best = max(scores, key=scores.get)
    return best if scores[best] else "unknown"


def classify_horizon(text: str) -> str:
    value = str(text or "")
    if any(word in value for word in ["日内", "今天", "早盘", "尾盘"]):
        return "intraday"
    if any(word in value for word in ["短线", "明天", "这两天", "1-3天"]):
        return "short"
    if any(word in value for word in ["波段", "一周", "几天"]):
        return "swing"
    if any(word in value for word in ["中线", "月", "季度"]):
        return "medium"
    return "unknown"


def first_sentence(text: str, limit: int = 140) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    parts = re.split(r"[。！？!?]\s*", cleaned, maxsplit=1)
    summary = parts[0].strip() or cleaned
    return summary[:limit]


def normalize_event(event: dict[str, Any], analyst: str) -> dict[str, Any]:
    content = str(event.get("content") or "")
    post_time = parse_time(str(event.get("post_time") or event.get("captured_at") or ""))
    return {
        "id": str(event.get("key") or event.get("canonical_key") or event.get("url") or ""),
        "analyst": analyst,
        "author": str(event.get("author") or analyst),
        "author_id": str(event.get("author_id") or ""),
        "post_time": post_time,
        "captured_at": parse_time(str(event.get("captured_at") or "")),
        "subject": str(event.get("subject") or ""),
        "url": str(event.get("url") or ""),
        "floor": str(event.get("floor") or ""),
        "content": content,
        "symbols": extract_symbols(content),
        "topics": extract_topics(content),
        "source_file": str(event.get("_source_file") or ""),
    }


def thesis_from_post(post: dict[str, Any]) -> dict[str, Any]:
    content = str(post.get("content") or "")
    return {
        "post_id": post["id"],
        "analyst": post["analyst"],
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "view_type": classify_view(content),
        "horizon": classify_horizon(content),
        "claim": first_sentence(content),
        "conditions": [],
        "invalidation": [],
        "symbols": post.get("symbols") or [],
        "topics": post.get("topics") or [],
    }


def connect_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        create table if not exists posts (
            id text primary key,
            analyst text,
            author_id text,
            post_time text,
            captured_at text,
            subject text,
            url text,
            floor text,
            content text,
            symbols_json text,
            topics_json text,
            source_file text
        )
        """
    )
    conn.execute(
        """
        create table if not exists theses (
            post_id text primary key,
            analyst text,
            created_at text,
            view_type text,
            horizon text,
            claim text,
            conditions_json text,
            invalidation_json text,
            symbols_json text,
            topics_json text
        )
        """
    )
    return conn


def upsert_posts(conn: sqlite3.Connection, posts: list[dict[str, Any]], theses: list[dict[str, Any]]) -> None:
    for post in posts:
        conn.execute(
            """
            insert or replace into posts
            (id, analyst, author_id, post_time, captured_at, subject, url, floor, content, symbols_json, topics_json, source_file)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post["id"],
                post["analyst"],
                post["author_id"],
                post["post_time"],
                post["captured_at"],
                post["subject"],
                post["url"],
                post["floor"],
                post["content"],
                json.dumps(post.get("symbols") or [], ensure_ascii=False),
                json.dumps(post.get("topics") or [], ensure_ascii=False),
                post.get("source_file") or "",
            ),
        )
    for thesis in theses:
        conn.execute(
            """
            insert or replace into theses
            (post_id, analyst, created_at, view_type, horizon, claim, conditions_json, invalidation_json, symbols_json, topics_json)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thesis["post_id"],
                thesis["analyst"],
                thesis["created_at"],
                thesis["view_type"],
                thesis["horizon"],
                thesis["claim"],
                json.dumps(thesis.get("conditions") or [], ensure_ascii=False),
                json.dumps(thesis.get("invalidation") or [], ensure_ascii=False),
                json.dumps(thesis.get("symbols") or [], ensure_ascii=False),
                json.dumps(thesis.get("topics") or [], ensure_ascii=False),
            ),
        )
    conn.commit()


def ingest(args: argparse.Namespace) -> None:
    kb_dir = Path(args.kb_dir)
    source = Path(args.source)
    analyst = args.analyst
    rows = read_jsonl(source)
    posts = []
    for row in rows:
        row["_source_file"] = str(source)
        post = normalize_event(row, analyst)
        if post["id"]:
            posts.append(post)
    posts = sorted({post["id"]: post for post in posts}.values(), key=lambda item: (item["post_time"], item["id"]))
    theses = [thesis_from_post(post) for post in posts]

    raw_target = kb_dir / "raw" / "nga" / f"{analyst}.jsonl"
    write_jsonl(raw_target, rows)
    write_jsonl(kb_dir / "normalized" / "posts.jsonl", posts)
    write_jsonl(kb_dir / "normalized" / "theses.jsonl", theses)
    conn = connect_db(kb_dir / "finance_kb.sqlite")
    upsert_posts(conn, posts, theses)
    conn.close()
    ensure_context(kb_dir, analyst)
    print(f"Ingested {len(posts)} posts for {analyst}")
    print(f"KB: {kb_dir.resolve()}")


def ensure_context(kb_dir: Path, analyst: str) -> None:
    context = kb_dir / "context"
    context.mkdir(parents=True, exist_ok=True)
    profiles = context / "analyst_profiles.md"
    if not profiles.exists():
        profiles.write_text(
            f"# Analyst Profiles\n\n## {analyst}\n\n- Source: NGA\n- Review windows: 1d, 3d, 5d, 20d\n- Notes:\n",
            encoding="utf-8",
        )
    watchlist = context / "watchlist.md"
    if not watchlist.exists():
        watchlist.write_text("# Watchlist\n\n", encoding="utf-8")
    positions = context / "positions.example.json"
    if not positions.exists():
        positions.write_text('{"note": "Do not commit real private positions."}\n', encoding="utf-8")


def load_normalized_posts(kb_dir: Path, analyst: str) -> list[dict[str, Any]]:
    rows = read_jsonl(kb_dir / "normalized" / "posts.jsonl")
    return [row for row in rows if row.get("analyst") == analyst]


def render_month_review(analyst: str, month: str, posts: list[dict[str, Any]]) -> str:
    topic_counts: dict[str, int] = defaultdict(int)
    symbol_counts: dict[str, int] = defaultdict(int)
    for post in posts:
        for topic in post.get("topics") or []:
            topic_counts[str(topic)] += 1
        for symbol in post.get("symbols") or []:
            symbol_counts[str(symbol)] += 1

    lines = [
        f"# {analyst} {month} Review Draft",
        "",
        "## Scope",
        "",
        f"- Posts: {len(posts)}",
        "- This is a draft generated from timestamped posts only.",
        "- Fill `At-Post Market Context` before using hindsight outcomes.",
        "",
        "## Topic Frequency",
        "",
    ]
    if topic_counts:
        lines.extend(f"- {topic}: {count}" for topic, count in sorted(topic_counts.items(), key=lambda item: (-item[1], item[0])))
    else:
        lines.append("- No topic keywords detected yet.")
    lines.extend(["", "## Mentioned Symbols", ""])
    if symbol_counts:
        lines.extend(f"- {symbol}: {count}" for symbol, count in sorted(symbol_counts.items(), key=lambda item: (-item[1], item[0]))[:30])
    else:
        lines.append("- No symbols detected yet.")
    lines.extend(["", "## Timeline", ""])
    for post in posts:
        topics = ", ".join(post.get("topics") or [])
        symbols = ", ".join(post.get("symbols") or [])
        lines.extend(
            [
                f"### {post.get('post_time') or 'unknown time'}",
                "",
                f"- URL: {post.get('url') or ''}",
                f"- Topics: {topics or 'none'}",
                f"- Symbols: {symbols or 'none'}",
                f"- Claim draft: {first_sentence(str(post.get('content') or ''))}",
                "",
                "#### At-Post Market Context",
                "",
                "- TODO: index state, sector heat, turnover, limit-up count.",
                "",
                "#### Future Outcome",
                "",
                "- TODO: 1d / 3d / 5d / 20d outcome.",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def review(args: argparse.Namespace) -> None:
    kb_dir = Path(args.kb_dir)
    analyst = args.analyst
    posts = load_normalized_posts(kb_dir, analyst)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for post in posts:
        grouped[month_key(str(post.get("post_time") or ""))].append(post)
    for month, month_posts in sorted(grouped.items()):
        target = kb_dir / "reviews" / analyst / f"{month}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_month_review(analyst, month, month_posts), encoding="utf-8")
        print(target)


def query(args: argparse.Namespace) -> None:
    kb_dir = Path(args.kb_dir)
    analyst = args.analyst
    keyword = str(args.keyword or "").strip().lower()
    posts = load_normalized_posts(kb_dir, analyst)
    if keyword:
        posts = [
            post
            for post in posts
            if keyword in str(post.get("content") or "").lower()
            or keyword in " ".join(str(topic).lower() for topic in post.get("topics") or [])
            or keyword in " ".join(str(symbol).lower() for symbol in post.get("symbols") or [])
        ]
    posts = sorted(posts, key=lambda item: str(item.get("post_time") or ""), reverse=True)[: args.limit]
    if not posts:
        print("No matching posts.")
        return
    for post in posts:
        topics = ", ".join(post.get("topics") or []) or "none"
        symbols = ", ".join(post.get("symbols") or []) or "none"
        print(f"{post.get('post_time') or 'unknown'} | {post.get('analyst')} | topics={topics} | symbols={symbols}")
        print(first_sentence(str(post.get("content") or ""), limit=180))
        if post.get("url"):
            print(post["url"])
        print()


def sample(args: argparse.Namespace) -> None:
    sample_path = Path(args.output)
    rows = [
        {
            "key": "sample-1",
            "author": "狼大",
            "author_id": "150058",
            "post_time": "2026-05-20 10:15:00",
            "subject": "盘中观察",
            "content": "今天算力和CPO继续走强，300308可以观察，但别追高，下午看量能能不能维持。",
            "url": "https://example.invalid/sample-1",
            "floor": "1",
            "captured_at": "2026-05-20T10:15:30",
        },
        {
            "key": "sample-2",
            "author": "狼大",
            "author_id": "150058",
            "post_time": "2026-05-21 14:20:00",
            "subject": "风险提示",
            "content": "机器人方向分歧加大，短线先观察，指数如果破位就要谨慎。",
            "url": "https://example.invalid/sample-2",
            "floor": "2",
            "captured_at": "2026-05-21T14:20:30",
        },
    ]
    write_jsonl(sample_path, rows)
    print(sample_path.resolve())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a private A-share finance KB from NGA watcher history.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Normalize source JSONL into KB files and SQLite.")
    ingest_parser.add_argument("--source", required=True, help="Source JSONL, for example AI_WORK_DIR/events/by_source/author_150058.jsonl.")
    ingest_parser.add_argument("--analyst", default="狼大")
    ingest_parser.add_argument("--kb-dir", default="finance-kb")
    ingest_parser.set_defaults(func=ingest)

    review_parser = subparsers.add_parser("review", help="Generate monthly Markdown review drafts.")
    review_parser.add_argument("--analyst", default="狼大")
    review_parser.add_argument("--kb-dir", default="finance-kb")
    review_parser.set_defaults(func=review)

    query_parser = subparsers.add_parser("query", help="Search normalized posts by keyword, topic, or symbol.")
    query_parser.add_argument("keyword", nargs="?", default="")
    query_parser.add_argument("--analyst", default="狼大")
    query_parser.add_argument("--kb-dir", default="finance-kb")
    query_parser.add_argument("--limit", type=int, default=10)
    query_parser.set_defaults(func=query)

    sample_parser = subparsers.add_parser("sample", help="Write a small sample source JSONL.")
    sample_parser.add_argument("--output", default="finance-kb/raw/nga/sample_wolf_history.jsonl")
    sample_parser.set_defaults(func=sample)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
