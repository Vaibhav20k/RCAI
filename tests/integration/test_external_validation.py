# Integration Tests for External Microservice Environment Adapter
import pytest
from simulator.external.adapter import ExternalEnvironmentAdapter
from observability.models import EvidenceSource

def test_external_telemetry_scraping_and_normalization():
    adapter = ExternalEnvironmentAdapter()
    
    # Scrape healthy baseline
    evidence = adapter.scrape_external_evidence("frontend-proxy")
    assert len(evidence) > 0
    assert evidence[0].provenance.collector == "ExternalPrometheusScraper"
    assert evidence[0].source == EvidenceSource.METRICS
    
    # Inject external anomaly and verify normalized evidence captures it
    adapter.inject_external_anomaly("recommendation-service", "cpu_utilization", 0.98)
    ev_anom = adapter.scrape_external_evidence("recommendation-service")
    cpu_ev = next((e for e in ev_anom if e.data.get("metric") == "cpu_utilization"), None)
    assert cpu_ev is not None
    assert cpu_ev.data["value"] == 0.98
    assert len(cpu_ev.provenance.hash_signature) > 0
