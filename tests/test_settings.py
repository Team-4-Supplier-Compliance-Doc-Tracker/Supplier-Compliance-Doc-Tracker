import json
from datetime import date

import pytest

from compliance.models import InputFileError
from compliance.settings import load_settings
from conftest import SETTINGS_JSON


def write_settings(tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(content))
    return path


def test_loads_settings(tmp_path):
    settings = load_settings(write_settings(tmp_path, SETTINGS_JSON))
    assert settings.expiring_soon_days == 45
    assert settings.document_types == ("quality_cert", "safety_cert", "env_declaration")
    assert settings.required_documents["mechanical"] == ("quality_cert", "env_declaration")
    assert set(settings.required_documents) == {"cables", "mechanical", "electrical", "semiconductors"}


def test_settings_missing_file_raises(tmp_path):
    path = tmp_path / "nope.json"
    with pytest.raises(InputFileError) as error:
        load_settings(path)
    assert str(path) in str(error.value)


def test_settings_invalid_json_raises(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"today": "2026-10-26",')
    with pytest.raises(InputFileError) as error:
        load_settings(path)
    assert str(path) in str(error.value)


def test_settings_missing_required_key_raises(tmp_path):
    content = {key: value for key, value in SETTINGS_JSON.items() if key != "required_documents"}
    with pytest.raises(InputFileError) as error:
        load_settings(write_settings(tmp_path, content))
    assert "required_documents" in str(error.value)


def test_today_parsed_as_date(tmp_path):
    settings = load_settings(write_settings(tmp_path, SETTINGS_JSON))
    assert settings.today == date(2026, 10, 26)


def test_expiring_types_parsed(tmp_path):
    settings = load_settings(write_settings(tmp_path, SETTINGS_JSON))
    assert settings.expiring_types == ("safety_cert", "env_declaration")
