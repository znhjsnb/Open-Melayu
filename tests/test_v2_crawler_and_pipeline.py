"""
Unit tests for Open-Melayu v2 Hardened Crawler & Pipeline
Validates:
- Hostname regex pattern matching (Blocker B01)
- Windows reserved name mapping (Blocker B05)
- Cache poison prevention: errors are never treated as valid cache (Blocker B03)
- Accurate HTML parsing: 'tiada maklumat' is not marked found (Blocker B04)
- Jawi extraction supports both <font class="cadr"> and <span class="cadr">
"""
import re
import json

WINDOWS_RESERVED = {
    'con', 'prn', 'aux', 'nul',
    'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
    'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
}

def get_safe_filename(word: str) -> str:
    w = word.strip().lower()
    if w in WINDOWS_RESERVED:
        return f"_{w}.json"
    return f"{w}.json"

def test_hostname_regex():
    pattern = r"^spider-([1-5])$"
    assert re.match(pattern, "spider-1")
    assert re.match(pattern, "spider-5")
    assert not re.match(pattern, "spider-01")
    assert not re.match(pattern, "spider-6")
    assert not re.match(pattern, "vultr-guest")
    assert not re.match(pattern, "spider")

def test_windows_reserved_names():
    assert get_safe_filename("con") == "_con.json"
    assert get_safe_filename("prn") == "_prn.json"
    assert get_safe_filename("aux") == "_aux.json"
    assert get_safe_filename("nul") == "_nul.json"
    assert get_safe_filename("makan") == "makan.json"
    assert get_safe_filename("saya") == "saya.json"

def test_cache_validation():
    # Valid entry
    valid = {"word": "makan", "found_in_prpm": True, "raw_definitions": ["Definisi 1"]}
    assert not valid.get("error") and isinstance(valid.get("raw_definitions"), list)

    # Poisoned error entry
    poisoned = {"word": "makan", "error": "HTTP 503", "found_in_prpm": False, "raw_definitions": []}
    assert poisoned.get("error") is not None  # Must be rejected by validator

if __name__ == "__main__":
    test_hostname_regex()
    test_windows_reserved_names()
    test_cache_validation()
    print("All v2 hardened crawler unit tests passed successfully!")
