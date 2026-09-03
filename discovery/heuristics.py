# RCAI Service Role and Database Classification Heuristics
from typing import List, Optional, Set

# Primary Signal: Exact and substring matching keywords for known database and cache engines.
# Case-insensitive comparison against image tags, container names, and compose service identifiers.
DATABASE_ENGINE_KEYWORDS: Set[str] = {
    "postgres",
    "postgresql",
    "psql",
    "mysql",
    "mariadb",
    "mongo",
    "mongodb",
    "redis",
    "memcached",
    "cassandra",
    "elasticsearch",
    "opensearch",
    "clickhouse",
    "cockroach",
    "cockroachdb",
    "scylla",
    "dynamodb"
}

# Secondary Signal: Standard default TCP ports for common relational and NoSQL datastores.
# Used strictly to confirm or corroborate database roles when container naming is ambiguous.
DATABASE_DEFAULT_PORTS: Set[int] = {
    5432,   # PostgreSQL default
    3306,   # MySQL / MariaDB default
    6379,   # Redis default
    6380,   # Redis TLS default
    27017,  # MongoDB default
    27018,  # MongoDB shard default
    11211,  # Memcached default
    9042,   # Cassandra native default
    9200,   # Elasticsearch / OpenSearch HTTP default
    8123,   # ClickHouse HTTP default
    26257,  # CockroachDB default
}

def detect_is_db_related(
    service_name: str,
    container_name: Optional[str] = None,
    image_name: Optional[str] = None,
    ports: Optional[List[int]] = None
) -> bool:
    """
    Heuristic Classifier for Database and Datastore Services.
    
    SAFETY-CRITICAL GATE RATIONALE:
    This flag directly determines whether `optimize_db_index` can ever be presented
    as an actionable candidate remediation playbook in the Playbook Selector.
    
    ASYMMETRIC RISK PROFILE:
    - False Positive (UNSAFE): Flagging an arbitrary web server or payment gateway as
      a database causes the agent to recommend SQL schema rebuilds or planner optimizations
      against services with no database handles, causing execution errors or harmful delays.
    - False Negative (SAFE): Missing a genuinely database-backed service simply prevents
      `optimize_db_index` from being offered automatically. The agent will safely fall back
      to restart or human escalation.
    
    Therefore, this heuristic is strictly conservative. It evaluates:
    1. Primary Signal: If the image repository/tag, container name, or service identifier
       explicitly matches a known database engine keyword (`postgres`, `redis`, etc.).
    2. Secondary Signal: If an exposed port matches a standard DB default port AND the name
       or image contains datastore indicators (e.g. 'db', 'store', 'cache').
    
    Returns:
        True if the service is conservatively classified as database/cache related;
        False otherwise.
    """
    candidate_tokens = []
    
    if service_name:
        candidate_tokens.extend(service_name.lower().replace("-", "_").split("_"))
    if container_name:
        # Strip leading slash common in Docker API container names (e.g. '/my-postgres')
        clean_cname = container_name.lstrip("/").lower().replace("-", "_")
        candidate_tokens.extend(clean_cname.split("_"))
    if image_name:
        # Clean image name (e.g., 'library/postgres:15-alpine' -> 'postgres')
        base_image = image_name.lower().split(":")[0].split("/")[-1]
        candidate_tokens.extend(base_image.replace("-", "_").split("_"))

    # Check primary keyword match:
    for token in candidate_tokens:
        for kw in DATABASE_ENGINE_KEYWORDS:
            if token == kw or kw in token:
                return True

    # Check secondary port match corroborated with datastore tokens:
    port_set = set(ports or [])
    has_db_port = bool(port_set.intersection(DATABASE_DEFAULT_PORTS))
    if has_db_port:
        datastore_hints = {"db", "data", "store", "cache", "sql", "rdbms", "nosql"}
        if any(hint in candidate_tokens for hint in datastore_hints):
            return True
        # Explicit generic service name 'database' or 'db'
        if service_name.lower() in ["db", "database", "datastore"]:
            return True

    return False
