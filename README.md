# m2m-migration-tool


**NOTE: This tool is experimental, please use it with caution**

Databricks Metastore-to-Metastore Migration Tool.

This tool is designed to help users migrate their Databricks Metastore assets to another Databricks Metastore. Currently it only supports external tables (views are not supported too).

## Installation

1. Install `hatch` as per documentation [here](https://hatch.pypa.io/latest/install/).
2. Clone this repository.
3. Run `hatch env create` to create a virtual environment.


## Usage

1. Make sure you're using the right shell, by running `hatch shell`.
2. Setup the env variables as described in `.env.example`.
2. Check the details in the `src/m2m_migration_tool/__main__.py` file, especially the `catalog` and `schema` renaming functions.
3. See the create statement by running `DRY_RUN=1 python -m m2m_migration_tool`.
4. Run the migration by running `python -m m2m_migration_tool`.
