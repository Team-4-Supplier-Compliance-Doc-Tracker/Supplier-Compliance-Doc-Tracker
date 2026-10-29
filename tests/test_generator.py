import json
import subprocess
import sys
from pathlib import Path

from conftest import DOCUMENTS_JSON, PARTS_JSON

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_data.py"


def run_generator(out_dir, seed=42):
    subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out_dir), "--seed", str(seed)],
        check=True,
    )


def test_generator_is_deterministic(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    run_generator(first)
    run_generator(second)
    for name in ("documents.json", "parts.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_generator_contains_required_ids(tmp_path):
    run_generator(tmp_path)
    documents = json.loads((tmp_path / "documents.json").read_text())
    parts = json.loads((tmp_path / "parts.json").read_text())

    document_ids = {record.get("document_id") for record in documents}
    part_numbers = {record.get("part_number") for record in parts}
    assert {record["document_id"] for record in DOCUMENTS_JSON} <= document_ids
    assert {record["part_number"] for record in PARTS_JSON} <= part_numbers
