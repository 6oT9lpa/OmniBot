from presentation.views.moderation_utils import parse_duration_to_seconds


def test_parse_duration_minutes():
    assert parse_duration_to_seconds("10m") == 600


def test_parse_duration_hours():
    assert parse_duration_to_seconds("1h") == 3600


def test_parse_duration_days():
    assert parse_duration_to_seconds("2d") == 172800


def test_parse_duration_seconds():
    assert parse_duration_to_seconds("600") == 600
