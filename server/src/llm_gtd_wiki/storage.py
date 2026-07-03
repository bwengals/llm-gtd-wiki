"""S3-backed storage for the wiki. One markdown file per object; keys mirror wiki paths 1:1
(e.g. `areas/home.md` -> object key `areas/home.md`).

Safety:
- path traversal / absolute paths rejected.
- writes under `raw/` refused (the operating contract treats raw/ as immutable).
- `edit` is a surgical string replace that errors unless `old` occurs exactly once.

Concurrency is last-write-wins (no locking) — fine for a single user across a couple of devices.
"""
from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from .config import Config

_TEXT_CT = "text/markdown; charset=utf-8"


class WikiError(Exception):
    """Tool-facing error with a clean message."""


def _clean_path(path: str, *, for_write: bool = False) -> str:
    p = (path or "").strip().lstrip("/")
    if p == "" or p.startswith("/") or "\\" in p or ".." in p.split("/"):
        raise WikiError(f"invalid path: {path!r}")
    if for_write and (p == "raw" or p.startswith("raw/")):
        raise WikiError("raw/ is immutable — writes there are not allowed")
    return p


class WikiStorage:
    def __init__(self, cfg: Config, client=None) -> None:
        if not cfg.wiki_bucket:
            raise WikiError("WIKI_BUCKET is not configured")
        self.bucket = cfg.wiki_bucket
        self.s3 = client or boto3.client("s3", region_name=cfg.cognito_region)

    # ---- reads ----
    def list_files(self) -> list[str]:
        keys: list[str] = []
        for page in self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return sorted(keys)

    def read(self, path: str) -> str:
        p = _clean_path(path)
        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key=p)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("NoSuchKey", "404", "NoSuchBucket"):
                raise WikiError(f"not found: {p}") from exc
            raise
        data = obj["Body"].read()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WikiError(
                f"{p} is a binary file ({len(data)} bytes) — stored, but not readable as text"
            ) from exc

    def search(self, query: str, path_prefix: str = "") -> list[str]:
        q = query.lower()
        hits: list[str] = []
        for key in self.list_files():
            if path_prefix and not key.startswith(path_prefix):
                continue
            if not key.endswith(".md"):
                continue
            try:
                text = self.read(key)
            except WikiError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if q in line.lower():
                    hits.append(f"{key}:{i}: {line.strip()}")
                    if len(hits) >= 100:
                        return hits
        return hits

    # ---- writes ----
    def write(self, path: str, content: str) -> None:
        p = _clean_path(path, for_write=True)
        self.s3.put_object(
            Bucket=self.bucket, Key=p, Body=content.encode("utf-8"), ContentType=_TEXT_CT
        )

    def edit(self, path: str, old: str, new: str) -> str:
        p = _clean_path(path, for_write=True)
        content = self.read(p)
        count = content.count(old)
        if count == 0:
            raise WikiError(f"old string not found in {p}")
        if count > 1:
            raise WikiError(
                f"old string occurs {count} times in {p} — add more surrounding "
                "context so it matches exactly once"
            )
        self.write(p, content.replace(old, new, 1))
        return f"edited {p}"

    def append(self, path: str, text: str) -> None:
        try:
            content = self.read(path)
        except WikiError:
            content = ""
        sep = "" if (content == "" or content.endswith("\n")) else "\n"
        self.write(path, content + sep + text.rstrip("\n") + "\n")
