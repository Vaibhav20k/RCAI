# Unit Tests for Database and Datastore Classification Heuristics
import pytest
from discovery.heuristics import detect_is_db_related

def test_primary_signal_database_engine_keywords():
    # Postgres variants
    assert detect_is_db_related(service_name="postgres") is True
    assert detect_is_db_related(service_name="order-db", image_name="postgres:15-alpine") is True
    assert detect_is_db_related(service_name="customer-database", container_name="/app_postgresql_1") is True
    
    # Redis / cache engines
    assert detect_is_db_related(service_name="redis") is True
    assert detect_is_db_related(service_name="cache-service", image_name="redis:7.0") is True
    assert detect_is_db_related(service_name="memcached-store") is True
    
    # Mongo / MySQL / Cassandra / ClickHouse
    assert detect_is_db_related(service_name="mongo") is True
    assert detect_is_db_related(service_name="mysql-primary") is True
    assert detect_is_db_related(service_name="mariadb-node") is True
    assert detect_is_db_related(service_name="clickhouse-analytics") is True
    assert detect_is_db_related(service_name="cassandra-cluster") is True

def test_secondary_signal_default_ports_with_datastore_hint():
    # Service with standard PostgreSQL port 5432 and hint 'db'
    assert detect_is_db_related(service_name="app-db", ports=[5432]) is True
    
    # Generic service named 'database' with port 5432
    assert detect_is_db_related(service_name="database", ports=[5432]) is True
    
    # Service with Redis port 6379 and hint 'cache'
    assert detect_is_db_related(service_name="session-cache", ports=[6379]) is True

def test_false_positive_prevention_on_standard_web_services():
    # Plain API gateway or web service (MUST NOT be classified as DB)
    assert detect_is_db_related(service_name="api-gateway", image_name="nginx:alpine", ports=[80, 443]) is False
    assert detect_is_db_related(service_name="order-service", image_name="python:3.11-slim", ports=[8001]) is False
    assert detect_is_db_related(service_name="payment-service", image_name="node:18", ports=[8002]) is False
    assert detect_is_db_related(service_name="frontend", image_name="myrepo/frontend:v2", ports=[3000]) is False
    assert detect_is_db_related(service_name="auth-service", ports=[8080]) is False

def test_edge_case_empty_and_none_inputs():
    assert detect_is_db_related(service_name="") is False
    assert detect_is_db_related(service_name="unknown", ports=[]) is False
    assert detect_is_db_related(service_name="worker", ports=None) is False
