import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast tests with no Spark")
    config.addinivalue_line("markers", "integration: Spark/Delta integration tests")
