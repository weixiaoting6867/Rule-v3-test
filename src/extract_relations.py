"""
Relation extraction from README files.

Identifies subject–predicate–object triples such as:
  - depends_on  ("X depends on Y", "X requires Y", "built with Y")
  - supports    ("X supports Y")
  - built_with  ("X is built with Y", "built on Y")
  - provides    ("X provides Y")
  - integrates_with ("X integrates with Y")
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Pattern definitions
# Each pattern is (predicate, compiled_regex).
# Named groups `subj` and `obj` are used when available; otherwise the
# surrounding sentence is searched for the subject using fallback logic.
# ---------------------------------------------------------------------------

_PATTERNS = [
    # depends_on
    ("depends_on", re.compile(
        r"(?P<subj>[A-Z][A-Za-z0-9_\-\.]+)\s+(?:depends\s+on|requires)\s+(?P<obj>[A-Za-z][A-Za-z0-9_\-\.]+)",
        re.IGNORECASE,
    )),
    ("depends_on", re.compile(
        r"(?:it\s+)?(?:depends\s+on|requires)\s+(?P<obj>[A-Za-z][A-Za-z0-9_\-\.]+)",
        re.IGNORECASE,
    )),
    # supports – object may include a version suffix such as "Python 3.8+" or "Python 3.8"
    # Pattern: named-entity token followed by an optional version number group
    ("supports", re.compile(
        r"(?P<subj>[A-Z][A-Za-z0-9_\-\.]+)\s+supports\s+"
        r"(?P<obj>[A-Z][A-Za-z0-9_\-\.][A-Za-z0-9_\-\.]*"
        r"(?:\s+[0-9][0-9\.+]*)?)(?:[,\.\s]|$)",  # optional version: e.g. " 3.8+"
        re.IGNORECASE,
    )),
    # built_with / built on
    ("built_with", re.compile(
        r"(?P<subj>[A-Z][A-Za-z0-9_\-\.]+)\s+is\s+built\s+with\s+(?P<obj>[A-Za-z][A-Za-z0-9_\-\.]+)",
        re.IGNORECASE,
    )),
    ("built_with", re.compile(
        r"built\s+(?:with|on)\s+(?P<obj>[A-Za-z][A-Za-z0-9_\-\.]+)",
        re.IGNORECASE,
    )),
    # provides – object can be a multi-word phrase, terminated by punctuation or
    # end-of-string (non-greedy to avoid over-capturing past sentence boundaries)
    ("provides", re.compile(
        r"(?P<subj>[A-Z][A-Za-z0-9_\-\.]+)\s+provides\s+(?P<obj>[a-zA-Z][A-Za-z0-9_\-\.\s]+?)(?:[,\.]|$)",
        re.IGNORECASE,
    )),
    # integrates_with
    ("integrates_with", re.compile(
        r"(?P<subj>[A-Z][A-Za-z0-9_\-\.]+)\s+integrates\s+with\s+(?P<obj>[A-Za-z][A-Za-z0-9_\-\.]+)",
        re.IGNORECASE,
    )),
    ("integrates_with", re.compile(
        r"(?:it\s+)?(?:also\s+)?integrates\s+with\s+(?P<obj>[A-Za-z][A-Za-z0-9_\-\.]+)",
        re.IGNORECASE,
    )),
]

# Confidence scores for extracted relations
_CONFIDENCE_HIGH = 0.95   # both subject and object captured by named groups
_CONFIDENCE_MEDIUM = 0.80  # subject inferred from context


_STOPWORDS = {
    "It", "This", "The", "A", "An", "These", "Those", "Its", "Their",
    "Also", "Both", "Each", "All", "and", "also", "or", "but",
    # Section headings that leak through
    "Installation", "Requirements", "Usage", "Features", "Optional",
    "Supported", "Support",
}


def _sentences(text: str):
    """Split *text* into sentences (simple rule-based splitter)."""
    # Split on '. ', '! ', '? ' followed by a capital letter or end-of-string
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    for s in raw:
        s = s.strip()
        if s:
            yield s


def _strip_markdown(text: str) -> str:
    """Remove code blocks, headings, and link syntax from Markdown text."""
    # Remove fenced code blocks (replace with single space)
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", " ", text)
    # Remove headings – keep text but neutralise the heading marker
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Remove Markdown links – keep link text
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # Remove bold/italic markers
    text = re.sub(r"[*_]{1,3}", "", text)
    # Collapse mid-sentence newlines (lines that don't end with punctuation)
    text = re.sub(r"(?<![.!?])\n(?=[a-z])", " ", text)
    return text


_PRONOUNS = {"It", "Its", "This", "These", "They", "Their", "That", "Those"}

# Pattern to find the main subject at the start of a sentence
_SENTENCE_SUBJECT_RE = re.compile(r"^([A-Z][A-Za-z0-9_\-\.]+)")


def _infer_subject_from_context(sentence: str, previous_subject: str) -> str:
    """Return the most likely subject when none is captured by the regex.

    If the sentence starts with a pronoun (It, This, …), falls back to
    *previous_subject*.  Otherwise returns the first capitalised non-stopword
    token at the start of the sentence.
    """
    m = _SENTENCE_SUBJECT_RE.match(sentence)
    first_word = m.group(1) if m else ""
    if first_word in _PRONOUNS or first_word in _STOPWORDS:
        return previous_subject
    if first_word and first_word not in _STOPWORDS:
        return first_word
    return previous_subject


def extract_relations(text: str) -> list:
    """Return a list of relation dicts extracted from *text*."""
    clean = _strip_markdown(text)
    relations = []
    seen = set()
    last_subject = ""

    for sentence in _sentences(clean):
        # Update the running subject from the sentence opening even when no
        # pattern matches (important for pronoun resolution in the next sentence)
        sentence_subject = _infer_subject_from_context(sentence, last_subject)
        if sentence_subject and sentence_subject not in _STOPWORDS:
            last_subject = sentence_subject

        for predicate, pattern in _PATTERNS:
            for m in pattern.finditer(sentence):
                groups = m.groupdict()
                obj = groups.get("obj", "").strip().rstrip(".,;")
                subj = groups.get("subj", "").strip()

                if not subj:
                    subj = _infer_subject_from_context(sentence, last_subject)
                if subj and subj not in _STOPWORDS:
                    last_subject = subj

                if not obj or not subj or subj in _STOPWORDS:
                    continue

                # For the 'supports' relation, require the object to start with
                # an uppercase letter to avoid capturing generic verbs/activities.
                if predicate == "supports" and not obj[0].isupper():
                    continue

                # Confidence is high when both subject and object are captured by
                # named regex groups; medium when the subject was inferred from context.
                confidence = (
                    _CONFIDENCE_HIGH
                    if groups.get("subj") and groups.get("obj")
                    else _CONFIDENCE_MEDIUM
                )

                key = (subj.lower(), predicate, obj.lower())
                if key in seen:
                    continue
                seen.add(key)

                relations.append(
                    {
                        "subject": subj,
                        "predicate": predicate,
                        "object": obj,
                        "sentence": sentence.strip(),
                        "confidence": confidence,
                    }
                )

    return relations


def process_file(path: Path, readme_id: int, repo: str = "") -> dict:
    """Extract relations from a single README file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "readme_id": readme_id,
        "repo": repo or path.stem,
        "source_file": path.name,
        "relations": extract_relations(text),
    }


def process_directory(input_dir: Path) -> list:
    """Extract relations from all *.md files in *input_dir*."""
    results = []
    md_files = sorted(input_dir.glob("*.md"))
    for idx, md_file in enumerate(md_files, start=1):
        results.append(process_file(md_file, readme_id=idx))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract relations from README Markdown files.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", metavar="FILE", help="Single README file to process.")
    group.add_argument(
        "--input-dir",
        metavar="DIR",
        help="Directory containing README *.md files to process.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Output JSON file path (default: stdout).",
    )
    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.input:
        path = Path(args.input)
        if not path.is_file():
            print(f"Error: '{path}' is not a file.", file=sys.stderr)
            sys.exit(1)
        result = process_file(path, readme_id=1)
        output = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        input_dir = Path(args.input_dir)
        if not input_dir.is_dir():
            print(f"Error: '{input_dir}' is not a directory.", file=sys.stderr)
            sys.exit(1)
        results = process_directory(input_dir)
        output = json.dumps(results, indent=2, ensure_ascii=False)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Written to {out_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
