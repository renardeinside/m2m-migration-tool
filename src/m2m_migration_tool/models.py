from dataclasses import dataclass
from databricks.sdk.service.catalog import TableType


@dataclass
class TableInfo:
    catalog_name: str
    schema_name: str
    table_name: str
    table_type: TableType
    create_statement: str
