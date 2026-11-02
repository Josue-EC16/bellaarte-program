"""SPEC04 synthetic observation scoring; no HTTP runner, model calls or DB imports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.services.leny_rag_evaluation import (compare_reports, digest, evaluate,
    snapshot_manifest, validate_corpus)  # noqa: E402

CORPUS = BACKEND / "tests/fixtures/leny_rag04_development.json"


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Artifact too large.")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-corpus")
    snapshot = commands.add_parser("snapshot", help="Source hashes only, including untracked files.")
    snapshot.add_argument("--output", type=Path, required=True)
    score = commands.add_parser("score", help="Score synthetic observations; does not generate them.")
    score.add_argument("--observations", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    comparison = commands.add_parser("compare")
    comparison.add_argument("--baseline", type=Path, required=True)
    comparison.add_argument("--candidate", type=Path, required=True)
    comparison.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-corpus":
            corpus = validate_corpus(read_json(CORPUS))
            print(json.dumps({"cases": len(corpus["cases"]), "corpus_sha256": digest(CORPUS),
                              "holdout_executed": False, "business_e2e_executed": False}))
            return 0
        if args.command == "snapshot":
            result = snapshot_manifest(BACKEND.parent)
        elif args.command == "score":
            result = evaluate(read_json(CORPUS), read_json(args.observations), corpus_sha256=digest(CORPUS))
        else:
            result = compare_reports(read_json(args.baseline), read_json(args.candidate))
        args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"scope": result.get("scope", result.get("schema_version")),
                          "acceptance": result.get("acceptance", result.get("candidate_acceptance")),
                          "holdout_executed": False, "business_e2e_executed": False}))
        return 2 if result.get("acceptance") == "not_accepted" else 0
    except (ValueError, OSError, KeyError, TypeError):
        # Artifact exceptions can contain input content or private local paths.
        print("Invalid or unsupported evaluation artifact; no model/database operation was performed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
