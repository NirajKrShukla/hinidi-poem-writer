from app.poem_rules import line_matra_count, validate_poem


def test_matra_count_returns_positive_for_hindi():
    assert line_matra_count("मन में आशा है") > 0


def test_validate_free_poem():
    result = validate_poem("मन में दीप जले\nराह नई बनती है", "free")
    assert result["line_count"] == 2
    assert len(result["matra_counts"]) == 2


def test_doha_validation_is_heuristic():
    result = validate_poem("राम नाम सुख देता\nमन को शांति देता", "doha")
    assert "13/11" in result["notes"][0]
