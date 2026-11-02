import results


def build(tmp_path, source="live"):
    path = tmp_path / "RESULTS.md"
    results.write_section("only", "Rows: 5", "make all", source, path=str(path))
    return path


def test_generated_section_verifies(tmp_path):
    assert results.verify(build(tmp_path).read_text(), required=("only",)) == []


def test_hand_edited_number_fails(tmp_path):
    text = build(tmp_path).read_text().replace("Rows: 5", "Rows: 500")
    assert any("hash" in problem for problem in results.verify(text, required=("only",)))


def test_text_outside_a_section_fails(tmp_path):
    text = build(tmp_path).read_text() + "Rows: 500\n"
    assert any("outside" in problem for problem in results.verify(text, required=("only",)))


def test_sample_data_section_fails(tmp_path):
    text = build(tmp_path, source="sample").read_text()
    assert any("sample" in problem for problem in results.verify(text, required=("only",)))


def test_rewriting_one_section_keeps_the_others(tmp_path):
    path = tmp_path / "RESULTS.md"
    results.write_section("a", "first", "c", "live", path=str(path))
    results.write_section("b", "second", "c", "live", path=str(path))
    results.write_section("a", "third", "c", "live", path=str(path))
    text = path.read_text()
    assert "third" in text and "second" in text and "first" not in text
