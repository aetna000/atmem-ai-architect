"""Scan release inputs, including nested archives, without printing client data."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import re
import subprocess
import tarfile
import zipfile

MAX_FILE = 128 * 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024 * 1024
PRIVATE_PATH = re.compile(r"(?:^|/)(?:\.env(?!\.example(?:/|$))(?:\.[^/]*)?|private-evidence|client-projects|client-data)(?:/|$)|\.(?:sqlite3?|db|key)$", re.I)
LOCAL_PATH = re.compile(r"(?:^|/)(?:\.git|\.local|node_modules|\.venv|\.memory-venv|__pycache__)(?:/|$)", re.I)


def scan(inputs, policy, package=False):
    rules = [re.compile(pattern, re.I) for pattern in policy.get("patterns", [])]
    hashes = set(policy.get("file_sha256", []))
    findings, count, total = [], 0, 0

    def fail(name, reason):
        findings.append({"entry": name, "reason": reason})

    def inspect(name, data, depth=0):
        nonlocal count, total
        count += 1
        total += len(data)
        if depth > 5 or len(data) > MAX_FILE or total > MAX_TOTAL:
            raise ValueError("Release scan resource limit exceeded")
        normalized = name.replace("\\", "/")
        if PRIVATE_PATH.search(normalized) or (package and LOCAL_PATH.search(normalized)):
            fail(name, "private_path")
        if hashlib.sha256(data).hexdigest() in hashes:
            fail(name, "private_file_digest")
        # Binary compression can contain coincidental short words. All bytes are
        # digest-checked; text policy applies to UTF-8 text and archive/document parts.
        # This is not an OCR or semantic document-classification claim.
        text = normalized
        try:
            decoded = data.decode("utf-8")
            if not any(ord(c) < 9 or 13 < ord(c) < 32 for c in decoded):
                text += "\n" + decoded
        except UnicodeDecodeError:
            pass
        if any(rule.search(text) for rule in rules):
            fail(name, "confidential_content")
        lower = name.lower()
        if zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    if member.file_size > MAX_FILE or total + member.file_size > MAX_TOTAL:
                        raise ValueError("Release archive expansion limit exceeded")
                    inspect(name + "!/" + member.filename, archive.read(member), depth + 1)
        elif lower.endswith((".tgz", ".tar.gz", ".tar")):
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
                for member in archive:
                    if member.issym() or member.islnk():
                        # Inspect link targets, never follow them. Bundled timezone
                        # databases use safe aliases; escaping links are rejected.
                        inspect(name + "!/" + member.name, member.linkname.encode(), depth + 1)
                        target = posixpath.normpath(posixpath.join(posixpath.dirname(member.name) if member.issym() else "", member.linkname))
                        if member.linkname.startswith(("/", "\\")) or target == ".." or target.startswith("../"):
                            fail(name + "!/" + member.name, "archive_link")
                    elif member.isfile():
                        if member.size > MAX_FILE or total + member.size > MAX_TOTAL:
                            raise ValueError("Release archive expansion limit exceeded")
                        inspect(name + "!/" + member.name, archive.extractfile(member).read(), depth + 1)
        elif lower.endswith((".zip", ".docx", ".xlsx", ".pptx")):
            raise ValueError("Release archive could not be inspected")

    for item in inputs:
        item, label = item if isinstance(item, tuple) else (item, str(item))
        p = Path(item)
        if p.is_symlink():
            fail(str(p), "filesystem_link")
        elif p.is_file():
            if p.stat().st_size > MAX_FILE:
                raise ValueError("Release file exceeds scan limit")
            inspect(label, p.read_bytes())
        else:
            raise ValueError("Release input is not a regular file")
    return {"passed": not findings, "files_and_archive_entries": count, "bytes_inspected": total,
            "client_policy_applied": bool(rules or hashes), "findings": findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--tracked", action="store_true")
    parser.add_argument("--policy")
    parser.add_argument("--require-policy", action="store_true")
    parser.add_argument("--package", action="store_true", help="Reject local runtime paths in distributables")
    parser.add_argument("--report", help="Local private report; never upload it as a public CI artifact")
    args = parser.parse_args()
    raw = Path(args.policy).read_text() if args.policy else os.environ.get("ATMEM_RELEASE_PRIVACY_POLICY", "")
    policy = json.loads(raw) if raw else {}
    if args.require_policy and not (policy.get("patterns") or policy.get("file_sha256")):
        raise ValueError("A private release policy is required")
    inputs = list(args.paths)
    if args.tracked:
        inputs += [p.decode() for p in subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0") if p]
    if not inputs:
        raise ValueError("Supply tracked files, a distribution directory, or release archives")
    expanded = []
    for name in inputs:
        p = Path(name)
        expanded += [(str(f), str(f.relative_to(p))) for f in sorted(p.rglob("*")) if f.is_file() or f.is_symlink()] if p.is_dir() else [(name, p.name if args.package else name)]
    result = scan(expanded, policy, args.package)
    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2) + "\n")
    # Findings can themselves contain private names. Only local reports retain paths.
    print(json.dumps({k: v for k, v in result.items() if k != "findings"} | {"finding_count": len(result["findings"])}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, re.error, zipfile.BadZipFile, tarfile.TarError):
        print("Release privacy scan could not complete; publication must stop.")
        raise SystemExit(2)
