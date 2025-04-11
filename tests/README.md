# Schwab-AI Portfolio Manager Tests

This directory contains tests for the Schwab-AI Portfolio Manager application.

## Running Tests

To run all tests:

```bash
python -m pytest
```

To run a specific test file:

```bash
python -m pytest tests/test_auth.py
```

To run tests with coverage:

```bash
python -m pytest --cov=src
```

## Test Organization

- `test_auth.py`: Tests for Schwab authentication
- `test_analysis.py`: Tests for portfolio analysis
- `test_trading.py`: Tests for trade execution

## Adding New Tests

When adding new tests, follow these guidelines:

1. Create a new test file named `test_<module>.py`
2. Use the `unittest` framework or `pytest`
3. Mock external dependencies (API calls, file I/O, etc.)
4. Include both success and error test cases
5. Aim for high test coverage

## Test Fixtures

Place test fixtures (sample data, mock responses, etc.) in the `tests/fixtures` directory.