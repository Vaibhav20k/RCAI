# End-to-End Integration Test for Demo Runner
import pytest
from scripts.demo import run_demo

def test_end_to_end_demo_execution():
    success = run_demo()
    assert success is True
