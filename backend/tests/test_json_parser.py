from utils.json_parser import safe_parse_json


def test_parses_plain_json():
    assert safe_parse_json('{"verdict": "bullish", "confidence": 0.7}') == {
        "verdict": "bullish",
        "confidence": 0.7,
    }


def test_strips_markdown_fences():
    text = '```json\n{"action": "buy"}\n```'
    assert safe_parse_json(text) == {"action": "buy"}


def test_extracts_json_surrounded_by_prose():
    text = 'Here is my analysis:\n{"action": "sell", "confidence": 0.6}\nHope this helps!'
    assert safe_parse_json(text) == {"action": "sell", "confidence": 0.6}


def test_escapes_raw_newlines_inside_strings():
    text = '{"argument": "line one\nline two\ttabbed"}'
    assert safe_parse_json(text) == {"argument": "line one\nline two\ttabbed"}


def test_falls_back_to_raw_response():
    assert safe_parse_json("not json at all") == {"raw_response": "not json at all"}
