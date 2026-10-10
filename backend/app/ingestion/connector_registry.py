from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SourceFamily, SourceIntent


def resolve_source_family(source_type: str) -> SourceFamily:
    """Classifies any connector or provider string into its Trulin Layer 1 SourceFamily."""
    st = (source_type or "").lower().strip()
    if st in ("file", "manual_upload", "pdf", "docx", "markdown", "confluence", "wiki", "notion", "google_docs"):
        return SourceFamily.DOCUMENT
    elif st in ("github", "git", "gitlab", "bitbucket"):
        return SourceFamily.DOCUMENT
    elif st in ("slack", "teams", "jira_comments", "email", "discord"):
        return SourceFamily.CONVERSATION
    elif st in ("jira", "jira_issues"):
        return SourceFamily.CONVERSATION
    elif st in (
        "tableau", "looker", "power_bi", "dbt", "airflow", "dagster",
        "kafka", "apache_kafka", "confluent", "lineage", "datadog", "newrelic", "sentry"
    ):
        return SourceFamily.METADATA_OPERATIONAL
    else:
        # Default for DBs, warehouses, object storage, NoSQL, CRM records
        return SourceFamily.STRUCTURED_DATA


def get_default_intent(source_type: str) -> SourceIntent:
    """Assigns the initial semantic intent for claim candidate scoping."""
    st = (source_type or "").lower().strip()
    if st in ("file", "manual_upload", "confluence", "wiki", "github", "git"):
        return SourceIntent.GOVERNANCE_POLICY
    elif st in ("slack", "teams", "discord"):
        return SourceIntent.PROPOSALS_DISCUSSIONS
    elif st in ("tableau", "looker", "power_bi"):
        return SourceIntent.ANALYTICS_METRIC
    elif st in ("dbt", "airflow", "lineage", "kafka"):
        return SourceIntent.FACTUAL_KNOWLEDGE
    else:
        return SourceIntent.OPERATIONAL_DATA


def get_default_capabilities(source_type: str) -> Dict[str, Any]:
    """Returns technical capability flags for the connector."""
    fam = resolve_source_family(source_type)
    if fam == SourceFamily.STRUCTURED_DATA:
        return {
            "supports_incremental": True,
            "supports_cdc": False,
            "supports_schema_discovery": True,
            "supports_granular_selection": True,
            "supports_snapshots": True,
            "pagination_type": "cursor",
            "native_identifier_field": "primary_key",
        }
    elif fam == SourceFamily.DOCUMENT:
        return {
            "supports_incremental": True,
            "supports_cdc": False,
            "supports_schema_discovery": True,
            "supports_granular_selection": True,
            "supports_snapshots": True,
            "pagination_type": "none",
            "native_identifier_field": "path_or_uri",
        }
    elif fam == SourceFamily.CONVERSATION:
        return {
            "supports_incremental": True,
            "supports_cdc": False,
            "supports_schema_discovery": True,
            "supports_granular_selection": True,
            "supports_snapshots": True,
            "pagination_type": "page",
            "native_identifier_field": "message_or_issue_id",
        }
    else:
        return {
            "supports_incremental": True,
            "supports_cdc": False,
            "supports_schema_discovery": True,
            "supports_granular_selection": True,
            "supports_snapshots": True,
            "pagination_type": "none",
            "native_identifier_field": "metric_or_entity_id",
        }


class ConnectorMetadata(BaseModel):
    id: str
    name: str
    category: str
    category_label: str
    family: str  # relational, storage, nosql, streaming, etl, orchestration, bi, observability, enterprise_app, ml_ai
    description: str
    default_port: Optional[int] = None
    default_auth: str = "password"  # password, oauth, token, iam, service_account
    doc_type: str = "data_contract"  # data_contract, stream_contract, crm_contract, pipeline_contract, metric_contract, quality_contract, ml_contract
    monitored_scope: str

    @property
    def source_family(self) -> SourceFamily:
        return resolve_source_family(self.id)

    @property
    def default_intent(self) -> SourceIntent:
        return get_default_intent(self.id)

    @property
    def capabilities(self) -> Dict[str, Any]:
        return get_default_capabilities(self.id)

    @property
    def required_fields(self) -> List[Dict[str, Any]]:
        if self.id in ("github", "git"):
            return [
                {"id": "repository", "label": "Repository (owner/repo)", "type": "text", "required": True},
                {"id": "branch", "label": "Branch", "type": "text", "required": False, "default": "main"},
                {"id": "access_token", "label": "Personal Access Token", "type": "password", "required": False},
            ]
        elif self.id in ("postgresql", "postgres", "mysql", "sql_server", "oracle", "snowflake"):
            return [
                {"id": "host", "label": "Host", "type": "text", "required": True},
                {"id": "port", "label": "Port", "type": "number", "default": self.default_port},
                {"id": "database", "label": "Database", "type": "text", "required": True},
                {"id": "username", "label": "Username", "type": "text", "required": True},
                {"id": "password", "label": "Password", "type": "password", "required": True},
            ]
        return [
            {"id": "host", "label": "Host / Endpoint", "type": "text", "required": True},
            {"id": "token", "label": "API Key / Token", "type": "password", "required": False},
        ]


# 104 Enterprise Connectors Taxonomy
CONNECTOR_CATALOG: List[ConnectorMetadata] = [
    # -------------------------------------------------------------
    # 1. Database / Data Warehouse (26)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="alloydb",
        name="AlloyDB for PostgreSQL",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Google Cloud managed PostgreSQL-compatible database service for demanding enterprise workloads.",
        default_port=5432,
        doc_type="data_contract",
        monitored_scope="AlloyDB tables, columnar indexes, foreign keys, partition constraints & ACID guarantees."
    ),
    ConnectorMetadata(
        id="athena",
        name="Amazon Athena",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Serverless interactive query service that makes it easy to analyze data in Amazon S3 using standard SQL.",
        default_port=443,
        default_auth="iam",
        doc_type="data_contract",
        monitored_scope="Athena Glue data catalogs, partitioned S3 tables, Iceberg datasets & SQL view contracts."
    ),
    ConnectorMetadata(
        id="documentdb",
        name="Amazon DocumentDB",
        category="database",
        category_label="Databases & Warehouses",
        family="nosql",
        description="Fast, scalable, highly available MongoDB-compatible document database service.",
        default_port=27017,
        doc_type="data_contract",
        monitored_scope="DocumentDB collections, JSON schema validators, replica set topologies & read preferences."
    ),
    ConnectorMetadata(
        id="dynamodb",
        name="Amazon DynamoDB",
        category="database",
        category_label="Databases & Warehouses",
        family="nosql",
        description="Fully managed serverless key-value and document database delivering single-digit millisecond performance.",
        default_port=443,
        default_auth="iam",
        doc_type="data_contract",
        monitored_scope="DynamoDB tables, partition keys, global secondary indexes (GSI) & TTL expiration rules."
    ),
    ConnectorMetadata(
        id="clickhouse",
        name="ClickHouse",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="High-performance column-oriented SQL database management system for real-time analytical reporting.",
        default_port=8123,
        doc_type="data_contract",
        monitored_scope="ClickHouse MergeTree engines, partition keys, TTL constraints & compression policies."
    ),
    ConnectorMetadata(
        id="cloud_sql_postgres",
        name="Cloud SQL for PostgreSQL",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Fully-managed PostgreSQL database service on Google Cloud Platform.",
        default_port=5432,
        doc_type="data_contract",
        monitored_scope="Cloud SQL schemas, table constraints, user roles, replica topologies & backup SLAs."
    ),
    ConnectorMetadata(
        id="cloudera_impala",
        name="Cloudera Impala",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Massively parallel processing (MPP) SQL query engine running on Apache Hadoop.",
        default_port=21050,
        doc_type="data_contract",
        monitored_scope="Impala metastore tables, Kudu/HDFS storage partitions & column stats."
    ),
    ConnectorMetadata(
        id="cratedb",
        name="CrateDB",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Distributed SQL database that makes it simple to store and analyze massive amounts of machine data.",
        default_port=4200,
        doc_type="data_contract",
        monitored_scope="CrateDB dynamic schemas, full-text indexes, shard allocations & time-series partitions."
    ),
    ConnectorMetadata(
        id="datastax",
        name="DataStax Enterprise",
        category="database",
        category_label="Databases & Warehouses",
        family="nosql",
        description="Always-on, scalable Apache Cassandra platform for enterprise real-time data.",
        default_port=9042,
        doc_type="data_contract",
        monitored_scope="DataStax keyspaces, CQL tables, partition tokens & clustering column constraints."
    ),
    ConnectorMetadata(
        id="databricks",
        name="Databricks",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Unified Analytics Platform powered by Apache Spark, Delta Lake and Unity Catalog.",
        default_port=443,
        default_auth="token",
        doc_type="data_contract",
        monitored_scope="Unity Catalog metastores, Delta Lake schemas, table constraints & time-travel retention."
    ),
    ConnectorMetadata(
        id="hive",
        name="Apache Hive",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Distributed data warehouse software for querying and managing large datasets residing in distributed storage.",
        default_port=10000,
        doc_type="data_contract",
        monitored_scope="Hive metastore schemas, external table locations, SerDe formats & partition specs."
    ),
    ConnectorMetadata(
        id="azure_cosmos_db",
        name="Microsoft Azure Cosmos DB",
        category="database",
        category_label="Databases & Warehouses",
        family="nosql",
        description="Globally distributed, multi-model database service for mission-critical applications.",
        default_port=443,
        default_auth="token",
        doc_type="data_contract",
        monitored_scope="Cosmos DB containers, partition keys, indexing policies & consistency level SLAs."
    ),
    ConnectorMetadata(
        id="azure_cosmos_nosql",
        name="Microsoft Azure Cosmos DB for NoSQL",
        category="database",
        category_label="Databases & Warehouses",
        family="nosql",
        description="Native JSON document database API for Microsoft Azure Cosmos DB.",
        default_port=443,
        default_auth="token",
        doc_type="data_contract",
        monitored_scope="Cosmos NoSQL documents, hierarchical partition keys & stored procedure contracts."
    ),
    ConnectorMetadata(
        id="mssql",
        name="Microsoft SQL Server",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Relational database management system developed by Microsoft.",
        default_port=1433,
        doc_type="data_contract",
        monitored_scope="MSSQL schemas, foreign key constraints, temporal tables & column encryption."
    ),
    ConnectorMetadata(
        id="mongodb_self",
        name="MongoDB (self-managed)",
        category="database",
        category_label="Databases & Warehouses",
        family="nosql",
        description="On-premises or self-hosted document database for flexible JSON schemas.",
        default_port=27017,
        doc_type="data_contract",
        monitored_scope="MongoDB collections, $jsonSchema validation rules, unique indexes & shard keys."
    ),
    ConnectorMetadata(
        id="mongodb_atlas",
        name="MongoDB Atlas",
        category="database",
        category_label="Databases & Warehouses",
        family="nosql",
        description="Multi-cloud developer data platform with managed MongoDB databases.",
        default_port=27017,
        doc_type="data_contract",
        monitored_scope="Atlas clusters, search indexes, collection schemas & automated backup SLAs."
    ),
    ConnectorMetadata(
        id="mysql",
        name="MySQL",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="World's most popular open-source relational database management system.",
        default_port=3306,
        doc_type="data_contract",
        monitored_scope="MySQL InnoDB schemas, foreign keys, auto-increment triggers & collation settings."
    ),
    ConnectorMetadata(
        id="on_prem_databases",
        name="On-Premises Databases",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Generic connector for private enterprise network database instances.",
        default_port=5432,
        doc_type="data_contract",
        monitored_scope="Corporate private intranet tables, data dictionary comments & access control policies."
    ),
    ConnectorMetadata(
        id="oracle",
        name="Oracle Database",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Multi-model database management system commonly used for running online transaction processing (OLTP).",
        default_port=1521,
        doc_type="data_contract",
        monitored_scope="Oracle schemas, table spaces, PL/SQL package definitions & constraints."
    ),
    ConnectorMetadata(
        id="postgresql",
        name="PostgreSQL",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Powerful, open source object-relational database system with strong ACID compliance.",
        default_port=5432,
        doc_type="data_contract",
        monitored_scope="PostgreSQL tables, schemas, PK/FK constraints, column nullability & retention rules."
    ),
    ConnectorMetadata(
        id="prestosql",
        name="PrestoSQL",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Distributed SQL query engine designed to query large data sets distributed over one or more heterogeneous data sources.",
        default_port=8080,
        doc_type="data_contract",
        monitored_scope="Presto catalog schemas, federated query contracts & connector connector mappings."
    ),
    ConnectorMetadata(
        id="sap_ase",
        name="SAP ASE",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="High-performance relational database management system for transaction-intensive environments.",
        default_port=5000,
        doc_type="data_contract",
        monitored_scope="SAP Sybase ASE tables, transaction logs, locking schemas & referential integrity."
    ),
    ConnectorMetadata(
        id="sap_hana",
        name="SAP HANA",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="In-memory, column-oriented relational database management system from SAP.",
        default_port=30015,
        doc_type="data_contract",
        monitored_scope="SAP HANA Calculation Views, CDS entities, column tables & tenant DB schemas."
    ),
    ConnectorMetadata(
        id="starburst",
        name="Starburst Enterprise",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Enterprise distribution of Trino providing fast SQL query engine for data lakes and data mesh architectures.",
        default_port=8443,
        doc_type="data_contract",
        monitored_scope="Starburst data products, governance roles, Trino federated catalogs & masking policies."
    ),
    ConnectorMetadata(
        id="teradata",
        name="Teradata Vantage",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Connected multi-cloud data analytics platform for enterprise analytics.",
        default_port=1025,
        doc_type="data_contract",
        monitored_scope="Teradata databases, primary index (PI) specifications, PPI partitioning & table columns."
    ),
    ConnectorMetadata(
        id="trino",
        name="Trino",
        category="database",
        category_label="Databases & Warehouses",
        family="relational",
        description="Fast distributed SQL query engine for big data analytics on data lakes.",
        default_port=8080,
        doc_type="data_contract",
        monitored_scope="Trino schemas, catalogs, distributed execution plans & view definitions."
    ),

    # -------------------------------------------------------------
    # 2. Data Warehouses / Lakehouses / Storage (9)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="redshift",
        name="Amazon Redshift",
        category="storage",
        category_label="Storage & Lakehouses",
        family="relational",
        description="Fast, simple, cost-effective data warehousing service in the AWS cloud.",
        default_port=5439,
        doc_type="data_contract",
        monitored_scope="Redshift tables, distribution keys, sort keys, Redshift Spectrum schemas & workload queues."
    ),
    ConnectorMetadata(
        id="s3",
        name="Amazon S3",
        category="storage",
        category_label="Storage & Lakehouses",
        family="storage",
        description="Object storage built to retrieve any amount of data from anywhere.",
        default_port=443,
        default_auth="iam",
        doc_type="data_contract",
        monitored_scope="S3 buckets, Parquet/CSV data layouts, lifecycle expiration policies & bucket encryption."
    ),
    ConnectorMetadata(
        id="dremio",
        name="Dremio",
        category="storage",
        category_label="Storage & Lakehouses",
        family="storage",
        description="SQL Lakehouse platform providing self-service semantic layer and query acceleration.",
        default_port=9047,
        doc_type="data_contract",
        monitored_scope="Dremio spaces, reflection acceleration datasets, Iceberg lakehouse tables & semantic models."
    ),
    ConnectorMetadata(
        id="bigquery",
        name="Google BigQuery",
        category="storage",
        category_label="Storage & Lakehouses",
        family="relational",
        description="Serverless, highly scalable, and cost-effective multi-cloud data warehouse.",
        default_port=443,
        default_auth="service_account",
        doc_type="data_contract",
        monitored_scope="BigQuery datasets, partitioned/clustered tables, materialized views & policy tags."
    ),
    ConnectorMetadata(
        id="gcs",
        name="Google Cloud Storage",
        category="storage",
        category_label="Storage & Lakehouses",
        family="storage",
        description="Unified object storage for developers and enterprises on Google Cloud.",
        default_port=443,
        default_auth="service_account",
        doc_type="data_contract",
        monitored_scope="GCS buckets, retention locks, object lifecycle rules & storage class transitions."
    ),
    ConnectorMetadata(
        id="iceberg",
        name="Apache Iceberg",
        category="storage",
        category_label="Storage & Lakehouses",
        family="storage",
        description="High-performance open table format for huge analytic tables with ACID transactions.",
        default_port=443,
        doc_type="data_contract",
        monitored_scope="Iceberg table schemas, partition specs, snapshot histories & schema evolution audits."
    ),
    ConnectorMetadata(
        id="synapse",
        name="Microsoft Azure Synapse Analytics",
        category="storage",
        category_label="Storage & Lakehouses",
        family="relational",
        description="Limitless analytics service that brings together enterprise data warehousing and Big Data analytics.",
        default_port=1433,
        doc_type="data_contract",
        monitored_scope="Synapse dedicated/serverless SQL pools, Lake databases & pipeline activities."
    ),
    ConnectorMetadata(
        id="sap_datasphere",
        name="SAP Datasphere",
        category="storage",
        category_label="Storage & Lakehouses",
        family="storage",
        description="Comprehensive data service built on the SAP Business Technology Platform for business data fabric.",
        default_port=443,
        doc_type="data_contract",
        monitored_scope="SAP Datasphere spaces, Analytic Models, Data Flows & business catalog definitions."
    ),
    ConnectorMetadata(
        id="snowflake",
        name="Snowflake",
        category="storage",
        category_label="Storage & Lakehouses",
        family="relational",
        description="Cloud Data Platform providing a single, global platform for data warehousing and data lakes.",
        default_port=443,
        doc_type="data_contract",
        monitored_scope="Snowflake databases, schemas, dynamic tables, masking policies & row access policies."
    ),

    # -------------------------------------------------------------
    # 3. ETL / Data Engineering (12)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="aws_glue",
        name="AWS Glue",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Serverless data integration service that makes it easy to discover, prepare, and combine data.",
        default_port=443,
        default_auth="iam",
        doc_type="pipeline_contract",
        monitored_scope="Glue Data Catalog databases, table classifiers, crawler schedules & ETL job definitions."
    ),
    ConnectorMetadata(
        id="alteryx",
        name="Alteryx",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Analytics automation platform that unifies analytics, data science, and process automation.",
        default_port=443,
        doc_type="pipeline_contract",
        monitored_scope="Alteryx Server workflows, analytic apps, input/output data sources & schedule SLAs."
    ),
    ConnectorMetadata(
        id="coalesce",
        name="Coalesce",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Data transformation tool built for scale, uniquely combining code automation and UI modeling.",
        default_port=443,
        doc_type="pipeline_contract",
        monitored_scope="Coalesce workspaces, transformation nodes, column lineage graphs & deployment jobs."
    ),
    ConnectorMetadata(
        id="fivetran",
        name="Fivetran",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Automated data movement platform moving data out of cloud applications into data warehouses.",
        default_port=443,
        default_auth="token",
        doc_type="pipeline_contract",
        monitored_scope="Fivetran connectors, destination sync status, schema migration logs & sync frequency SLAs."
    ),
    ConnectorMetadata(
        id="hightouch",
        name="Hightouch",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Reverse ETL platform syncing data from warehouses to customer-facing business tools.",
        default_port=443,
        default_auth="token",
        doc_type="pipeline_contract",
        monitored_scope="Hightouch sync configurations, target CRM mappings, run frequencies & error thresholds."
    ),
    ConnectorMetadata(
        id="informatica_cdi",
        name="Informatica CDI",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Informatica Cloud Data Integration providing enterprise ETL/ELT capabilities.",
        default_port=443,
        default_auth="token",
        doc_type="pipeline_contract",
        monitored_scope="Informatica mappings, task flows, source/target endpoints & data quality rules."
    ),
    ConnectorMetadata(
        id="informatica_powercenter",
        name="Informatica PowerCenter",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Enterprise data integration platform for building enterprise data warehouses.",
        default_port=6005,
        doc_type="pipeline_contract",
        monitored_scope="PowerCenter repository workflows, sessions, source definitions & transformation logic."
    ),
    ConnectorMetadata(
        id="matillion",
        name="Matillion",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Data transformation platform purpose-built for cloud data warehouses.",
        default_port=443,
        doc_type="pipeline_contract",
        monitored_scope="Matillion ETL/ELT orchestration pipelines, transformation components & version tags."
    ),
    ConnectorMetadata(
        id="azure_data_factory",
        name="Microsoft Azure Data Factory",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Cloud-based data integration service that allows you to create data-driven workflows.",
        default_port=443,
        default_auth="service_account",
        doc_type="pipeline_contract",
        monitored_scope="Azure Data Factory pipelines, linked services, data flows & trigger schedules."
    ),
    ConnectorMetadata(
        id="ssis",
        name="SSIS (SQL Server Integration Services)",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Microsoft enterprise-level data integration and data transformation solution.",
        default_port=1433,
        doc_type="pipeline_contract",
        monitored_scope="SSISDB catalog packages, execution environments, data flow tasks & parameters."
    ),
    ConnectorMetadata(
        id="talend",
        name="Talend",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Next-generation data integration platform combining data quality, big data, and cloud integration.",
        default_port=443,
        doc_type="pipeline_contract",
        monitored_scope="Talend Management Console tasks, data governance plans, artifacts & execution plans."
    ),
    ConnectorMetadata(
        id="dbt",
        name="dbt (data build tool)",
        category="etl",
        category_label="ETL & Pipelines",
        family="etl",
        description="Transform data in your warehouse using SQL select statements, version control and automated testing.",
        default_port=443,
        doc_type="pipeline_contract",
        monitored_scope="dbt models, manifest schema tests (not_null, unique, accepted_values), freshness & documentation."
    ),

    # -------------------------------------------------------------
    # 4. Data Lineage / Orchestration (9)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="mwaa_openlineage",
        name="Amazon MWAA OpenLineage",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Managed Workflows for Apache Airflow with OpenLineage observability emitter.",
        default_port=443,
        default_auth="iam",
        doc_type="pipeline_contract",
        monitored_scope="MWAA DAGs, task lineage events, input/output dataset assertions & run durations."
    ),
    ConnectorMetadata(
        id="airflow_openlineage",
        name="Apache Airflow OpenLineage",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Standard Apache Airflow platform emitting OpenLineage operational dataset metadata.",
        default_port=8080,
        doc_type="pipeline_contract",
        monitored_scope="Airflow DAG definitions, schedule intervals, dataset sensors & SLA policies."
    ),
    ConnectorMetadata(
        id="flink_openlineage",
        name="Apache Flink OpenLineage",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Stream processing framework emitting real-time continuous pipeline lineage.",
        default_port=8081,
        doc_type="pipeline_contract",
        monitored_scope="Flink streaming jobs, checkpoint SLAs, source/sink schema lineage & watermark rules."
    ),
    ConnectorMetadata(
        id="spark_openlineage",
        name="Apache Spark OpenLineage",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Multi-language engine for executing data engineering and machine learning on large datasets.",
        default_port=4040,
        doc_type="pipeline_contract",
        monitored_scope="Spark application plans, RDD transformations, table write assertions & driver metrics."
    ),
    ConnectorMetadata(
        id="astronomer_openlineage",
        name="Astronomer OpenLineage",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Managed Astro cloud data orchestration platform powered by Apache Airflow.",
        default_port=443,
        default_auth="token",
        doc_type="pipeline_contract",
        monitored_scope="Astronomer deployments, workspace DAGs, task failure alerts & cross-DAG dependencies."
    ),
    ConnectorMetadata(
        id="dagster",
        name="Dagster",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Cloud-native orchestrator designed for developing and maintaining data assets.",
        default_port=3000,
        doc_type="pipeline_contract",
        monitored_scope="Dagster software-defined assets, auto-materialize policies, checks & freshness SLAs."
    ),
    ConnectorMetadata(
        id="generic_openlineage",
        name="Generic OpenLineage",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Standard OpenLineage REST API specification for custom enterprise orchestrators.",
        default_port=443,
        doc_type="pipeline_contract",
        monitored_scope="Standardized OpenLineage RunEvents, Job Facets, Dataset Facets & Column Lineage."
    ),
    ConnectorMetadata(
        id="cloud_composer_openlineage",
        name="Google Cloud Composer OpenLineage",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Google Cloud managed Airflow service with integrated OpenLineage telemetry.",
        default_port=443,
        default_auth="service_account",
        doc_type="pipeline_contract",
        monitored_scope="Composer environment DAGs, BigQuery operators, Dataproc steps & pipeline health."
    ),
    ConnectorMetadata(
        id="dataflow",
        name="Google Dataflow",
        category="orchestration",
        category_label="Orchestration & Lineage",
        family="orchestration",
        description="Fully managed streaming analytics service based on Apache Beam.",
        default_port=443,
        default_auth="service_account",
        doc_type="pipeline_contract",
        monitored_scope="Dataflow job graph templates, pipeline execution parameters & autoscaling policies."
    ),

    # -------------------------------------------------------------
    # 5. Messaging & Schema (7)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="aiven_kafka",
        name="Aiven Kafka",
        category="messaging",
        category_label="Streaming & Messaging",
        family="streaming",
        description="Fully managed Apache Kafka service across AWS, GCP, and Azure.",
        default_port=9092,
        default_auth="token",
        doc_type="stream_contract",
        monitored_scope="Aiven Kafka topics, Schema Registry subjects, ACL rules & retention window policies."
    ),
    ConnectorMetadata(
        id="amazon_msk",
        name="Amazon MSK",
        category="messaging",
        category_label="Streaming & Messaging",
        family="streaming",
        description="Amazon Managed Streaming for Apache Kafka providing secure streaming cluster infrastructure.",
        default_port=9092,
        default_auth="iam",
        doc_type="stream_contract",
        monitored_scope="MSK clusters, partition topology, MSK Connect connectors & IAM access policies."
    ),
    ConnectorMetadata(
        id="apache_kafka",
        name="Apache Kafka",
        category="messaging",
        category_label="Streaming & Messaging",
        family="streaming",
        description="Distributed event streaming platform used by thousands of companies for high-performance data pipelines.",
        default_port=9092,
        doc_type="stream_contract",
        monitored_scope="Kafka topics, partition layouts, consumer groups, retention SLAs & serialization schemas."
    ),
    ConnectorMetadata(
        id="confluent_kafka",
        name="Confluent Kafka",
        category="messaging",
        category_label="Streaming & Messaging",
        family="streaming",
        description="Enterprise event streaming platform and Confluent Cloud cloud data streaming service.",
        default_port=9092,
        default_auth="token",
        doc_type="stream_contract",
        monitored_scope="Confluent stream topics, ksqlDB streams, Stream Governance tags & Schema Registry."
    ),
    ConnectorMetadata(
        id="azure_event_hubs",
        name="Microsoft Azure Event Hubs",
        category="messaging",
        category_label="Streaming & Messaging",
        family="streaming",
        description="Fully managed, real-time data ingestion service that's simple, trusted, and scalable.",
        default_port=443,
        default_auth="token",
        doc_type="stream_contract",
        monitored_scope="Event Hub namespaces, event hubs, consumer groups, message retention & capture policies."
    ),
    ConnectorMetadata(
        id="redpanda_kafka",
        name="Redpanda Kafka",
        category="messaging",
        category_label="Streaming & Messaging",
        family="streaming",
        description="C++ powered streaming platform compatible with Kafka APIs, delivering low-latency throughput.",
        default_port=9092,
        doc_type="stream_contract",
        monitored_scope="Redpanda topics, raft replication groups, Schema Registry & WASM data transforms."
    ),
    ConnectorMetadata(
        id="confluent_schema_registry",
        name="Confluent Schema Registry",
        category="messaging",
        category_label="Streaming & Messaging",
        family="streaming",
        description="Centralized schema management serving Avro, JSON Schema, and Protobuf formats.",
        default_port=8081,
        doc_type="stream_contract",
        monitored_scope="Schema Registry subjects, compatibility levels (BACKWARD/FULL), versions & schema rules."
    ),

    # -------------------------------------------------------------
    # 6. BI / Analytics (19)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="quicksight",
        name="Amazon QuickSight",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Serverless, machine learning-powered BI service built for the cloud.",
        default_port=443,
        default_auth="iam",
        doc_type="metric_contract",
        monitored_scope="QuickSight dashboards, SPICE datasets, calculated fields & visual user permissions."
    ),
    ConnectorMetadata(
        id="anaplan",
        name="Anaplan",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Cloud-native enterprise planning and performance management software platform.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Anaplan models, line items, multi-dimensional modules & forecasting formulas."
    ),
    ConnectorMetadata(
        id="domo",
        name="Domo",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Cloud-based business management suite that integrates with multiple data sources.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Domo cards, dashboards, Magic ETL data flows & dataset refresh schedules."
    ),
    ConnectorMetadata(
        id="cognos",
        name="IBM Cognos Analytics",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="AI-fueled business intelligence platform that supports the entire analytics cycle.",
        default_port=9300,
        doc_type="metric_contract",
        monitored_scope="Cognos packages, report specifications, dashboard queries & data modules."
    ),
    ConnectorMetadata(
        id="looker",
        name="Looker",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Enterprise platform for BI, data applications, and embedded analytics with LookML semantic layer.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="LookML views, explores, dimensions, measures, derived tables & dashboard tiles."
    ),
    ConnectorMetadata(
        id="metabase",
        name="Metabase",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Easy, open source way for everyone in your company to ask questions and learn from data.",
        default_port=3000,
        doc_type="metric_contract",
        monitored_scope="Metabase questions, dashboards, collections, custom expressions & pulse alerts."
    ),
    ConnectorMetadata(
        id="microstrategy",
        name="MicroStrategy",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Enterprise analytics and mobility platform delivering modern reporting and hyperintelligence.",
        default_port=443,
        doc_type="metric_contract",
        monitored_scope="MicroStrategy dossiers, schema attributes, metrics, cubes & security filters."
    ),
    ConnectorMetadata(
        id="ms_fabric",
        name="Microsoft Fabric",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="All-in-one analytics solution for enterprises that covers everything from data movement to data science.",
        default_port=443,
        default_auth="service_account",
        doc_type="metric_contract",
        monitored_scope="Fabric Lakehouses, Power BI semantic models, KQL databases & OneLake workspaces."
    ),
    ConnectorMetadata(
        id="power_bi",
        name="Microsoft Power BI",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Interactive data visualization software product developed by Microsoft.",
        default_port=443,
        default_auth="service_account",
        doc_type="metric_contract",
        monitored_scope="Power BI workspaces, reports, DAX calculated measures, dataset lineage & refresh schedules."
    ),
    ConnectorMetadata(
        id="ssrs",
        name="Microsoft SSRS",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Server-based report generating software system from Microsoft.",
        default_port=80,
        doc_type="metric_contract",
        monitored_scope="SSRS RDL report definitions, shared datasets, parameter lists & data source credentials."
    ),
    ConnectorMetadata(
        id="mode",
        name="Mode Analytics",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Collaborative data science and interactive business intelligence platform.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Mode reports, SQL queries, Python notebooks, visual charts & sharing permissions."
    ),
    ConnectorMetadata(
        id="omni",
        name="Omni",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Next-generation BI tool providing a shared data model with SQL and drag-and-drop flexibility.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Omni shared data models, workbooks, topics, dimensions & measure definitions."
    ),
    ConnectorMetadata(
        id="qlik_sense_cloud",
        name="Qlik Sense Cloud",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Cloud-native analytics platform powered by the Qlik Associative Engine.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Qlik Cloud apps, sheets, master items, dimensions, measures & data connections."
    ),
    ConnectorMetadata(
        id="qlik_sense_enterprise",
        name="Qlik Sense Enterprise (Windows)",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="On-premises and private cloud enterprise deployment of Qlik Sense.",
        default_port=443,
        doc_type="metric_contract",
        monitored_scope="Qlik QMC app streams, reload tasks, master dimensions & user access allocations."
    ),
    ConnectorMetadata(
        id="redash",
        name="Redash",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Open source data visualization and collaboration tool for querying data sources.",
        default_port=5000,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Redash queries, visualizations, dashboards & scheduled query executions."
    ),
    ConnectorMetadata(
        id="sigma",
        name="Sigma Computing",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Cloud analytics and BI platform providing a spreadsheet interface on cloud warehouses.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Sigma workbooks, dataset models, calculations, warehouse lineage & permissions."
    ),
    ConnectorMetadata(
        id="sisense",
        name="Sisense",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Analytics platform that empowers companies to build custom embedded analytics experiences.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Sisense ElastiCubes, dashboards, widgets, formulas & security data access rules."
    ),
    ConnectorMetadata(
        id="tableau",
        name="Tableau",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="Visual analytics platform transforming the way we use data to solve problems.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="Tableau Server/Cloud workbooks, published data sources, custom SQL & calculated fields."
    ),
    ConnectorMetadata(
        id="thoughtspot",
        name="ThoughtSpot",
        category="bi",
        category_label="BI & Analytics",
        family="bi",
        description="AI-Powered Analytics platform providing natural language search and automated insights.",
        default_port=443,
        default_auth="token",
        doc_type="metric_contract",
        monitored_scope="ThoughtSpot Worksheets, Liveboards, Answers, formulas & verification tags."
    ),

    # -------------------------------------------------------------
    # 7. Data Governance / Privacy / Observability (14)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="altr",
        name="ALTR",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Cloud data control and policy automation platform providing automated data access controls.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="ALTR data access policies, masking rules, rate limits & anomalous query alerts."
    ),
    ConnectorMetadata(
        id="sagemaker_unified_studio",
        name="AWS SageMaker Unified Studio",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Integrated environment for building, governing, and discovering data & AI assets.",
        default_port=443,
        default_auth="iam",
        doc_type="quality_contract",
        monitored_scope="Unified Studio domain assets, governance catalog terms, access grants & project scopes."
    ),
    ConnectorMetadata(
        id="anomalo",
        name="Anomalo",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Automated data quality monitoring platform that surfaces data issues before consumers notice.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Anomalo table checks, unsupervised ML anomaly detectors, null checks & metric drift rules."
    ),
    ConnectorMetadata(
        id="ataccama",
        name="Ataccama",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Unified data quality, master data management, and data catalog governance platform.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Ataccama business glossary, DQ rule dimensions (validity, completeness) & MDM entities."
    ),
    ConnectorMetadata(
        id="bigid",
        name="BigID",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Data intelligence platform for privacy, security, compliance, and governance automation.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="BigID PII/PHI classifiers, GDPR/CCPA regulatory tags, data risk scores & catalog metadata."
    ),
    ConnectorMetadata(
        id="bigeye",
        name="Bigeye",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Enterprise data observability platform tracking data quality SLAs across warehouses.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Bigeye metrics, autothreshold bounds, data freshness SLAs & schema change detectors."
    ),
    ConnectorMetadata(
        id="cyera",
        name="Cyera",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="AI-powered data security and governance platform for multi-cloud data estates.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Cyera sensitive data classifications, exposure risk assessments & compliance controls."
    ),
    ConnectorMetadata(
        id="elementary",
        name="Elementary Cloud",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="dbt-native data observability platform providing automated anomaly detection in your warehouse.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Elementary anomaly test results, volume anomaly alerts, schema changes & test failure history."
    ),
    ConnectorMetadata(
        id="google_knowledge_catalog",
        name="Google Knowledge Catalog",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Unified metadata management and data discovery service on Google Cloud (formerly Dataplex).",
        default_port=443,
        default_auth="service_account",
        doc_type="quality_contract",
        monitored_scope="Knowledge Catalog taxonomy tag templates, Dataplex data quality tasks & lineage."
    ),
    ConnectorMetadata(
        id="immuta",
        name="Immuta",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Data security platform providing automated access control, data masking, and audit monitoring.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Immuta subscription policies, dynamic data masking rules, purpose grants & audit logs."
    ),
    ConnectorMetadata(
        id="monte_carlo",
        name="Monte Carlo",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="End-to-end data observability platform identifying and preventing data downtime.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Monte Carlo monitors, freshness/volume anomaly alerts, schema diffs & incident triage."
    ),
    ConnectorMetadata(
        id="qualytics",
        name="Qualytics",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Autonomous data quality and data surveillance platform for enterprise datasets.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Qualytics surveillance rules, confidence scores, anomaly remediations & audit trail."
    ),
    ConnectorMetadata(
        id="soda",
        name="Soda Core & Soda Cloud",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Data quality testing and monitoring framework powered by SodaCL contracts.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="SodaCL agreement checks, metric thresholds, automated scan schedules & check pass rates."
    ),
    ConnectorMetadata(
        id="telmai",
        name="Telmai",
        category="governance",
        category_label="Governance & Quality",
        family="observability",
        description="Real-time data observability platform designed for hybrid data architectures.",
        default_port=443,
        default_auth="token",
        doc_type="quality_contract",
        monitored_scope="Telmai real-time metrics, streaming data drift alerts, schema evolution & value distributions."
    ),

    # -------------------------------------------------------------
    # 8. Knowledge / CRM / ERP (9)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="glean",
        name="Glean",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Enterprise search and knowledge discovery platform indexing all corporate tools.",
        default_port=443,
        default_auth="token",
        doc_type="crm_contract",
        monitored_scope="Glean enterprise search indexes, corporate knowledge articles & entity resolution mappings."
    ),
    ConnectorMetadata(
        id="netsuite",
        name="NetSuite ERP",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Cloud ERP business management suite for finance, accounting, and operations.",
        default_port=443,
        default_auth="token",
        doc_type="crm_contract",
        monitored_scope="NetSuite SuiteTalk entities (Invoices, Customers, Purchase Orders) & accounting policies."
    ),
    ConnectorMetadata(
        id="salesforce",
        name="Salesforce CRM",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Customer relationship management platform for sales, service, and marketing.",
        default_port=443,
        default_auth="oauth",
        doc_type="crm_contract",
        monitored_scope="Salesforce Standard/Custom SObjects (Contract, Account, Case, Opportunity) & validation rules."
    ),
    ConnectorMetadata(
        id="sap_bw_4hana",
        name="SAP BW/4HANA",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Next-generation enterprise data warehouse solution optimized for the SAP HANA platform.",
        default_port=30015,
        doc_type="crm_contract",
        monitored_scope="SAP BW InfoObjects, CompositeProviders, Advanced DataStore Objects (ADSO) & queries."
    ),
    ConnectorMetadata(
        id="sap_ecc",
        name="SAP ECC",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Enterprise Resource Planning central component for managing core business processes.",
        default_port=3300,
        doc_type="crm_contract",
        monitored_scope="SAP ECC transparent tables (BKPF, BSEG, KNA1, VBAK), IDoc structures & BAPI interfaces."
    ),
    ConnectorMetadata(
        id="sap_s4hana",
        name="SAP S/4HANA",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Next-generation ERP business suite designed to run simplified on SAP HANA.",
        default_port=443,
        default_auth="oauth",
        doc_type="crm_contract",
        monitored_scope="SAP S/4HANA Core Data Services (CDS) views, business partner entities & finance journal rules."
    ),
    ConnectorMetadata(
        id="confluence",
        name="Atlassian Confluence",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Team workspace where knowledge and collaboration meet for documentation and policies.",
        default_port=443,
        default_auth="token",
        doc_type="crm_contract",
        monitored_scope="Confluence Spaces, policy documentation articles, architectural guidelines & release plans."
    ),
    ConnectorMetadata(
        id="jira",
        name="Atlassian Jira",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Issue tracking and agile project management tool for development and IT operations.",
        default_port=443,
        default_auth="token",
        doc_type="crm_contract",
        monitored_scope="Jira projects, issue types, incident post-mortems, SLAs & compliance runbooks."
    ),
    ConnectorMetadata(
        id="github",
        name="GitHub",
        category="crm_erp",
        category_label="CRM & ERP",
        family="enterprise_app",
        description="Version control and collaboration platform for software development and policy-as-code.",
        default_port=443,
        default_auth="token",
        doc_type="crm_contract",
        monitored_scope="GitHub repository markdown policies, OpenAPI specifications, security docs & CI/CD standards."
    ),

    # -------------------------------------------------------------
    # 9. ML / AI (2)
    # -------------------------------------------------------------
    ConnectorMetadata(
        id="sagemaker",
        name="Amazon SageMaker",
        category="ml_ai",
        category_label="ML & AI",
        family="ml_ai",
        description="Fully managed machine learning service for building, training, and deploying ML models.",
        default_port=443,
        default_auth="iam",
        doc_type="ml_contract",
        monitored_scope="SageMaker Model Registry cards, Feature Store feature groups, Model Monitor drift rules."
    ),
    ConnectorMetadata(
        id="sagemaker_studio_ml",
        name="AWS SageMaker Unified Studio ML",
        category="ml_ai",
        category_label="ML & AI",
        family="ml_ai",
        description="End-to-end ML governance, foundation model evaluation, and lifecycle tracking.",
        default_port=443,
        default_auth="iam",
        doc_type="ml_contract",
        monitored_scope="SageMaker AI governance cards, foundation model benchmark ratings & safety guardrail checks."
    ),
]


class ConnectorRegistry:
    """Central registry and connector discovery engine for all 104 enterprise data sources."""

    _catalog_by_id: Dict[str, ConnectorMetadata] = {c.id: c for c in CONNECTOR_CATALOG}

    @classmethod
    def get_all(cls) -> List[ConnectorMetadata]:
        return CONNECTOR_CATALOG

    @classmethod
    def get_by_id(cls, connector_id: str) -> Optional[ConnectorMetadata]:
        clean_id = (connector_id or "").strip().lower().replace("-", "_").replace(" ", "_")
        if clean_id in cls._catalog_by_id:
            return cls._catalog_by_id[clean_id]
        
        # Alias matching
        aliases = {
            "git": "github",
            "github_repo": "github",
            "repo": "github",
            "postgres": "postgresql",
            "psql": "postgresql",
            "mongodb": "mongodb_atlas",
            "mongo": "mongodb_atlas",
            "kafka": "apache_kafka",
            "confluent": "confluent_kafka",
            "mongo": "mongodb_atlas",
            "sfdc": "salesforce",
            "s3_bucket": "s3",
            "bq": "bigquery",
            "gcs_bucket": "gcs",
            "airflow": "airflow_openlineage",
            "powerbi": "power_bi",
            "sagemaker_ai": "sagemaker",
            "soda_core": "soda",
            "soda_cloud": "soda",
        }
        target_id = aliases.get(clean_id)
        if target_id and target_id in cls._catalog_by_id:
            return cls._catalog_by_id[target_id]

        return None

    @classmethod
    def find_connector(cls, query: str) -> Optional[ConnectorMetadata]:
        """Find a connector by ID, alias, or fuzzy name match."""
        direct = cls.get_by_id(query)
        if direct:
            return direct
        q = (query or "").strip().lower()
        if not q:
            return None
        for c in CONNECTOR_CATALOG:
            if q in c.id.lower() or q in c.name.lower():
                return c
        return None

    @classmethod
    def get_categories(cls) -> List[Dict[str, Any]]:
        categories = [
            {"id": "all", "label": "All Connectors", "count": len(CONNECTOR_CATALOG)},
            {"id": "database", "label": "Databases & Warehouses", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "database")},
            {"id": "storage", "label": "Storage & Lakehouses", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "storage")},
            {"id": "etl", "label": "ETL & Pipelines", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "etl")},
            {"id": "orchestration", "label": "Orchestration & Lineage", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "orchestration")},
            {"id": "messaging", "label": "Streaming & Messaging", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "messaging")},
            {"id": "bi", "label": "BI & Analytics", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "bi")},
            {"id": "governance", "label": "Governance & Quality", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "governance")},
            {"id": "crm_erp", "label": "Knowledge, CRM & Repos", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "crm_erp")},
            {"id": "ml_ai", "label": "ML & AI", "count": sum(1 for c in CONNECTOR_CATALOG if c.category == "ml_ai")},
        ]
        return categories
