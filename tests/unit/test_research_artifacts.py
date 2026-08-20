# Unit Tests for Research Artifacts Generator
import pathlib
import pytest
from benchmark.reports.generate_artifacts import generate_all_research_artifacts

def test_generate_all_research_artifacts_creates_files(tmp_path):
    out_dir = tmp_path / "results"
    paths = generate_all_research_artifacts(output_dir=str(out_dir))
    assert pathlib.Path(paths["benchmark_json"]).exists()
    assert pathlib.Path(paths["ablation_json"]).exists()
    assert pathlib.Path(paths["table1_tex"]).exists()
    assert pathlib.Path(paths["table2_tex"]).exists()
    t1_content = pathlib.Path(paths["table1_tex"]).read_text(encoding="utf-8")
    assert "\\begin{tabular}" in t1_content
    assert "Proposed Active RCAI" in t1_content
