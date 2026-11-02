"""Write and verify RESULTS.md sections.

Each script owns one section. A section's marker holds a hash of its body, so a
hand-edited number or a section produced from sample data fails verification.

Usage: python src/results.py RESULTS.md
"""
import hashlib
import os
import re
import sys

REQUIRED = ("ingestion", "analysis", "anomaly", "validation")
SECTION = re.compile(
    r"<!-- section:(\w+) source=(\w+) sha256=(\w+) -->\n(.*?)<!-- end:\1 -->\n", re.DOTALL
)
HEADER = "# Results\n\nEvery number below is written by the command named in its section.\n\n"


def results_path():
    return os.getenv("RESULTS_PATH", "RESULTS.md")


def data_source(con):
    """Return 'sample' if the database holds offline sample rows, otherwise 'live'."""
    sample = con.execute(
        "SELECT count(*) FROM raw.service_requests WHERE source_layer LIKE 'sample%'"
    ).fetchone()[0]
    return "sample" if sample else "live"


def digest(body):
    return hashlib.sha256(body.encode()).hexdigest()


def write_section(name, body, command, source, path=None):
    """Replace one section, keeping the others and the REQUIRED order."""
    path = path or results_path()
    existing = open(path).read() if os.path.exists(path) else ""
    sections = {match[0]: match for match in SECTION.findall(existing)}
    body = f"## {name.title()}\n\nCommand: `{command}`\n\n{body.strip()}\n\n"
    sections[name] = (name, source, digest(body), body)
    with open(path, "w") as out:
        out.write(HEADER)
        for key in [*REQUIRED, *sorted(set(sections) - set(REQUIRED))]:
            if key in sections:
                _, src, sha, text = sections[key]
                out.write(f"<!-- section:{key} source={src} sha256={sha} -->\n{text}<!-- end:{key} -->\n\n")


def verify(text, required=REQUIRED):
    """Return a list of problems with a RESULTS.md document."""
    found = {match[0]: match for match in SECTION.findall(text)}
    problems = [f"missing section: {name}" for name in required if name not in found]
    for name, source, sha, body in found.values():
        if source == "sample":
            problems.append(f"{name}: built from sample data")
        if digest(body) != sha:
            problems.append(f"{name}: body does not match its hash (edited by hand?)")
    # Text outside a section could carry a number no script wrote.
    if SECTION.sub("", text).strip() != HEADER.strip():
        problems.append("text found outside generated sections")
    return problems


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else results_path()
    if not os.path.exists(target):
        sys.exit(f"{target} does not exist")
    issues = verify(open(target).read())
    if issues:
        sys.exit("\n".join(issues))
    print(f"{target} verified")
