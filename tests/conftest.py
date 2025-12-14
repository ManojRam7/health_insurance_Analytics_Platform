import os
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    # If you already configure spark in notebooks, keep it simple here.
    # You can also pass env vars for warehouse/metastore if needed.
    spark = SparkSession.builder.getOrCreate()
    return spark
