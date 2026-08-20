# Tests for RCAI v2 Scenario Taxonomy Registry
import pytest
from benchmark.scenarios.taxonomy import (
    global_taxonomy,
    TaxonomyEntry,
    ScenarioFamily,
    ScenarioDifficulty,
    DatasetSplit,
    TaxonomyRegistry
)

def test_global_taxonomy_initial_entries():
    entries = global_taxonomy.list_all()
    assert len(entries) >= 5
    global_taxonomy.validate_integrity()

def test_unique_scenario_ids_enforced():
    reg = TaxonomyRegistry()
    e1 = TaxonomyEntry(
        scenario_id="test_sc_1",
        family=ScenarioFamily.DATABASE,
        variant="variant_a",
        difficulty=ScenarioDifficulty.EASY,
        ground_truth_root_cause="Test DB root cause",
        root_cause_service="order-service",
        root_cause_category="database"
    )
    reg.register(e1)

    with pytest.raises(ValueError, match="Duplicate scenario_id"):
        reg.register(e1)

def test_taxonomy_queries_by_family_and_split():
    db_scenarios = global_taxonomy.get_by_family(ScenarioFamily.DATABASE)
    assert len(db_scenarios) >= 1
    assert db_scenarios[0].family == ScenarioFamily.DATABASE

    dev_scenarios = global_taxonomy.get_by_split(DatasetSplit.DEVELOPMENT)
    assert len(dev_scenarios) >= 5

def test_taxonomy_payment_and_adversarial_queries():
    payment_sc = global_taxonomy.get_payment_scenarios()
    assert len(payment_sc) >= 2
    assert all(sc.payment_domain for sc in payment_sc)

    adversarial_sc = global_taxonomy.get_adversarial_scenarios()
    assert isinstance(adversarial_sc, list)
