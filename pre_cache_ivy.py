#!/usr/bin/env python3
"""
Pre-cache Ivy dependencies before running the pipeline.
This runs ONCE and caches all packages so subsequent runs don't trigger Ivy resolution.
Run this before your first pipeline run: python pre_cache_ivy.py
"""

import os
import sys
from pyspark.sql import SparkSession

def pre_cache_dependencies():
    """Initialize Spark with all required packages to cache them in Ivy."""
    
    packages = ",".join([
        "io.delta:delta-spark_2.12:3.1.0",
        "org.apache.hadoop:hadoop-azure:3.3.4",
        "com.azure:azure-storage-blob:12.19.0",
        "com.azure:azure-identity:1.10.0"
    ])
    
    print("=" * 70)
    print("PRE-CACHING IVY DEPENDENCIES (This runs once)")
    print("=" * 70)
    print(f"\nCaching packages: {packages}\n")
    
    try:
        spark = (
            SparkSession.builder
                .appName("health-ivy-cache")
                .master("local[1]")
                .config("spark.jars.packages", packages)
                .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
                .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
                .config("spark.driver.bindAddress", "127.0.0.1")
                .config("spark.ui.port", "0")
                .getOrCreate()
        )
        
        spark.sparkContext.setLogLevel("ERROR")
        
        # Quick test to verify caching worked
        df = spark.createDataFrame([(1, "test")], ["id", "value"])
        df.show(1)
        
        spark.stop()
        
        print("\n" + "=" * 70)
        print("SUCCESS: All dependencies cached in ~/.ivy2/cache/")
        print("   Future runs will NOT show Ivy resolution output.")
        print("=" * 70)
        
    except Exception as e:
        print(f"ERROR during caching: {e}")
        sys.exit(1)

if __name__ == "__main__":
    pre_cache_dependencies()
