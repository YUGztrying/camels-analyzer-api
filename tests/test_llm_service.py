"""
Tests for llm_service.py — mocks the Anthropic API to test JSON parsing,
error handling, and input validation.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

VALID_BANK_JSON = {
    "name": "Banque de Test",
    "country": "Senegal",
    "fiscal_year": "2023",
    "currency": "XOF",
    "total_assets": 1000000,
    "total_equity": 120000,
    "net_income": 10000,
    "gross_loans": 600000,
    "deposits": 700000,
    "npls_mn": 20000,
    "loan_loss_provisions": -25000,
    "interest_income": 80000,
    "interest_expenses": 30000,
    "net_interest_income": 50000,
    "operating_expenses": 30000,
    "operating_income": 64000,
}


def _make_mock_response(text):
    """Create a mock Anthropic response."""
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


def _make_mock_workbook():
    """Create a mock openpyxl workbook."""
    mock_ws = MagicMock()
    mock_ws.iter_rows.return_value = [("test", "data")]
    mock_workbook = MagicMock()
    mock_workbook.sheetnames = ["Sheet1"]
    mock_workbook.__getitem__ = lambda self, key: mock_ws
    return mock_workbook


class TestJsonParsing:
    """Test the JSON extraction logic from Claude's response."""

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test-key'})
    @patch('llm_service.client')
    @patch('openpyxl.load_workbook')
    def test_clean_json_response(self, mock_wb, mock_client):
        mock_wb.return_value = _make_mock_workbook()
        mock_client.messages.create.return_value = _make_mock_response(
            json.dumps(VALID_BANK_JSON)
        )
        from llm_service import extract_bank_data_from_file
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(b'dummy')
            tmp_path = f.name
        try:
            result = extract_bank_data_from_file(tmp_path)
            assert result["name"] == "Banque de Test"
            assert result["total_assets"] == 1000000
        finally:
            os.unlink(tmp_path)

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test-key'})
    @patch('llm_service.client')
    @patch('openpyxl.load_workbook')
    def test_json_in_code_block(self, mock_wb, mock_client):
        mock_wb.return_value = _make_mock_workbook()
        response_text = f"Here's the data:\n```json\n{json.dumps(VALID_BANK_JSON)}\n```"
        mock_client.messages.create.return_value = _make_mock_response(response_text)
        from llm_service import extract_bank_data_from_file
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(b'dummy')
            tmp_path = f.name
        try:
            result = extract_bank_data_from_file(tmp_path)
            assert result["name"] == "Banque de Test"
        finally:
            os.unlink(tmp_path)

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test-key'})
    @patch('llm_service.client')
    @patch('openpyxl.load_workbook')
    def test_json_with_surrounding_text(self, mock_wb, mock_client):
        mock_wb.return_value = _make_mock_workbook()
        response_text = f"I found the data:\n{json.dumps(VALID_BANK_JSON)}\nThat's it."
        mock_client.messages.create.return_value = _make_mock_response(response_text)
        from llm_service import extract_bank_data_from_file
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(b'dummy')
            tmp_path = f.name
        try:
            result = extract_bank_data_from_file(tmp_path)
            assert result["name"] == "Banque de Test"
        finally:
            os.unlink(tmp_path)

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test-key'})
    @patch('llm_service.client')
    @patch('openpyxl.load_workbook')
    def test_invalid_json_raises(self, mock_wb, mock_client):
        mock_wb.return_value = _make_mock_workbook()
        mock_client.messages.create.return_value = _make_mock_response(
            "Sorry, I couldn't extract any data from this document."
        )
        from llm_service import extract_bank_data_from_file
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(b'dummy')
            tmp_path = f.name
        try:
            with pytest.raises(Exception, match="Invalid JSON"):
                extract_bank_data_from_file(tmp_path)
        finally:
            os.unlink(tmp_path)


class TestInputValidation:
    """Test the validate_extracted_data function."""

    def test_valid_data_passes(self):
        from llm_service import validate_extracted_data
        errors = validate_extracted_data(VALID_BANK_JSON)
        assert len(errors) == 0

    def test_missing_total_assets(self):
        from llm_service import validate_extracted_data
        data = {**VALID_BANK_JSON, "total_assets": None}
        errors = validate_extracted_data(data)
        assert any("total_assets" in e for e in errors)

    def test_negative_total_assets(self):
        from llm_service import validate_extracted_data
        data = {**VALID_BANK_JSON, "total_assets": -100}
        errors = validate_extracted_data(data)
        assert any("total_assets" in e for e in errors)

    def test_missing_total_equity(self):
        from llm_service import validate_extracted_data
        data = {**VALID_BANK_JSON, "total_equity": None}
        errors = validate_extracted_data(data)
        assert any("total_equity" in e for e in errors)

    def test_equity_exceeds_assets(self):
        from llm_service import validate_extracted_data
        data = {**VALID_BANK_JSON, "total_equity": 2000000, "total_assets": 1000000}
        errors = validate_extracted_data(data)
        assert any("equity" in e.lower() and "assets" in e.lower() for e in errors)

    def test_npl_exceeds_gross_loans(self):
        from llm_service import validate_extracted_data
        data = {**VALID_BANK_JSON, "npls_mn": 700000, "gross_loans": 600000}
        errors = validate_extracted_data(data)
        assert any("npl" in e.lower() for e in errors)

    def test_string_coerced_to_number(self):
        from llm_service import validate_extracted_data
        data = {**VALID_BANK_JSON, "total_assets": "1000000"}
        errors = validate_extracted_data(data)
        assert len(errors) == 0

    def test_empty_dict(self):
        from llm_service import validate_extracted_data
        errors = validate_extracted_data({})
        assert len(errors) > 0

    def test_completely_missing_fields(self):
        from llm_service import validate_extracted_data
        errors = validate_extracted_data({"name": "Test"})
        assert any("total_assets" in e for e in errors)

    def test_negative_interest_expenses_warning(self):
        from llm_service import validate_extracted_data
        data = {**VALID_BANK_JSON, "interest_expenses": -30000}
        errors = validate_extracted_data(data)
        assert any("interest_expenses" in e for e in errors)

    def test_net_income_exceeds_assets_warning(self):
        from llm_service import validate_extracted_data
        data = {**VALID_BANK_JSON, "net_income": 2000000, "total_assets": 1000000}
        errors = validate_extracted_data(data)
        assert any("net income" in e.lower() for e in errors)
