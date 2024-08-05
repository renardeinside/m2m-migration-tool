from typing import Iterator
from dotenv import load_dotenv
from dataclasses import dataclass
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import CatalogInfo, TableType
import os
from loguru import logger

from m2m_migration_tool.models import TableInfo
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

load_dotenv()


@dataclass
class Api:
    source: WorkspaceClient
    dest: WorkspaceClient


required_env_vars = [
    "DATABRICKS_SOURCE_HOST",
    "DATABRICKS_SOURCE_CLIENT_ID",
    "DATABRICKS_SOURCE_CLIENT_SECRET",
    "DATABRICKS_SOURCE_WAREHOUSE_ID",
    "DATABRICKS_DEST_HOST",
    "DATABRICKS_DEST_CLIENT_ID",
    "DATABRICKS_DEST_CLIENT_SECRET",
    "DATABRICKS_DEST_WAREHOUSE_ID",
]

for var in required_env_vars:
    if var not in os.environ:
        raise ValueError(f"Environment variable {var} is required")


@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(multiplier=0.1, max=2))
def get_create_statement(
    api: Api, catalog_name: str, schema_name: str, table_name: str
) -> str:
    query = api.source.statement_execution.execute_statement(
        f"SHOW CREATE TABLE {catalog_name}.{schema_name}.{table_name}",
        warehouse_id=os.environ["DATABRICKS_SOURCE_WAREHOUSE_ID"],
    )
    return query.result.data_array[0][0]


def list_tables_and_views(api: Api) -> Iterator[TableInfo]:
    # if you would like to choose catalogs manually, you can do it here
    # like this catalog_infos = [CatalogInfo(name="main")]
    # otherwise, you can list all catalogs
    # api.source.catalogs.list()
    catalog_infos = None
    assert catalog_infos is not None, "Please specify catalog_infos"
    for catalog in catalog_infos:
        if catalog.name not in ["system", "system_billing_usage", "hive_metastore"]:
            logger.info(f"Listing tables and views in catalog {catalog.name}")
            for schema in api.source.schemas.list(catalog.name):
                logger.info(f"Listing tables and views in schema {schema.name}")
                if "schema" != "information_schema":
                    for table in api.source.tables.list(catalog.name, schema.name):
                        if table.table_type in [TableType.EXTERNAL]:
                            create_stmt = get_create_statement(
                                api,
                                table.catalog_name,
                                table.schema_name,
                                table.name,
                            )
                            table_info = TableInfo(
                                catalog_name=table.catalog_name,
                                schema_name=table.schema_name,
                                table_name=table.name,
                                table_type=table.table_type,
                                create_statement=create_stmt,
                            )
                            yield table_info
                        else:
                            logger.warning(
                                f"Skipping object {table.name} because it is not an external table"
                            )


def new_catalog_name(existing_catalog_name: str) -> str:
    # add your custom renaming logic here if needed
    return f"{existing_catalog_name}"


def new_schema_name(existing_schema_name: str) -> str:
    # add your custom renaming logic here if needed
    return f"{existing_schema_name}"


def apply_migration(api: Api, tables: Iterator[TableInfo]):
    for table in tables:
        new_catalog = new_catalog_name(table.catalog_name)
        new_schema = new_schema_name(table.schema_name)
        new_table = table.table_name
        new_create_stmt = table.create_statement.replace(
            "CREATE TABLE", "CREATE TABLE IF NOT EXISTS"
        ).replace(
            f"{table.catalog_name}.{table.schema_name}.{table.table_name}",
            f"{new_catalog}.{new_schema}.{new_table}",
        )
        logger.info(f"Creating table {new_catalog}.{new_schema}.{new_table}")
        if not os.environ.get("DRY_RUN"):
            api.dest.statement_execution.execute_statement(
                new_create_stmt, warehouse_id=os.environ["DATABRICKS_DEST_WAREHOUSE_ID"]
            )
            logger.info(f"Table {new_catalog}.{new_schema}.{new_table} created")
        else:
            logger.info(new_create_stmt)
            logger.info(
                f"Table {new_catalog}.{new_schema}.{new_table} not created (dry run)"
            )


def main():
    logger.info("Starting migration tool")
    logger.info("Loading environment variables")
    api = Api(
        WorkspaceClient(
            host=os.environ["DATABRICKS_SOURCE_HOST"],
            client_id=os.environ["DATABRICKS_SOURCE_CLIENT_ID"],
            client_secret=os.environ["DATABRICKS_SOURCE_CLIENT_SECRET"],
        ),
        WorkspaceClient(
            host=os["DATABRICKS_DEST_HOST"],
            client_id=os["DATABRICKS_DEST_CLIENT_ID"],
            client_secret=os["DATABRICKS_DEST_CLIENT_SECRET"],
        ),
    )

    # first - list all tables and views in the source
    tables = list_tables_and_views(api)
    # second - apply migration
    apply_migration(api, tables)


if __name__ == "__main__":
    main()
