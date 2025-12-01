# ===============================================
# utils_silver.py  (Local / VS Code compatible)
# Enterprise Silver Layer utilities
# ===============================================

from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window as W
from pyspark.sql import DataFrame
from datetime import datetime

# ------------------------------------------------
# CONFIG (edit once for your environment)
# ------------------------------------------------
def build_paths(storage_account):

    CONTAINER_BRONZE = "rawdata"
    CONTAINER_SILVER = "silverdata"

    paths_bronze = {
        "policies":  f"abfss://{CONTAINER_BRONZE}@{storage_account}.dfs.core.windows.net/policies",
        "members":   f"abfss://{CONTAINER_BRONZE}@{storage_account}.dfs.core.windows.net/members",
        "claims":    f"abfss://{CONTAINER_BRONZE}@{storage_account}.dfs.core.windows.net/claims",
        "providers": f"abfss://{CONTAINER_BRONZE}@{storage_account}.dfs.core.windows.net/providers",
    }

    reference_base = f"abfss://{CONTAINER_SILVER}@{storage_account}.dfs.core.windows.net/reference"

    paths_silver = {
        "policies":  f"abfss://{CONTAINER_SILVER}@{storage_account}.dfs.core.windows.net/policies",
        "members":   f"abfss://{CONTAINER_SILVER}@{storage_account}.dfs.core.windows.net/members",
        "claims":    f"abfss://{CONTAINER_SILVER}@{storage_account}.dfs.core.windows.net/claims",
        "providers": f"abfss://{CONTAINER_SILVER}@{storage_account}.dfs.core.windows.net/providers",
        "_quarantine": f"abfss://{CONTAINER_SILVER}@{storage_account}.dfs.core.windows.net/_quarantine",
        "_metrics":    f"abfss://{CONTAINER_SILVER}@{storage_account}.dfs.core.windows.net/_metrics",

        # keep base
        "_reference": reference_base,

        # add flat keys
        "_ref_dim_channel": f"{reference_base}/dim_channel",
        "_ref_dim_product_line": f"{reference_base}/dim_product_line"
    }

    return paths_bronze, paths_silver


# ------------------------------------------------
# 1) BASIC DQ + SCHEMA
# ------------------------------------------------
def null_percentage(df: DataFrame) -> DataFrame:
    total = df.count()
    return df.select([
        (F.count(F.when(F.col(c).isNull(), c)) / F.lit(max(total, 1))).alias(c)
        for c in df.columns
    ])

def enforce_schema(df: DataFrame, target_schema: StructType) -> DataFrame:
    """
    Cast to schema. If missing columns appear in schema, add as null.
    """
    select_exprs = []
    for field in target_schema.fields:
        if field.name in df.columns:
            select_exprs.append(F.col(field.name).cast(field.dataType).alias(field.name))
        else:
            select_exprs.append(F.lit(None).cast(field.dataType).alias(field.name))
    return df.select(*select_exprs)

def check_duplicates(df: DataFrame, key_cols: list) -> DataFrame:
    dup_count = df.groupBy(key_cols).count().filter("count > 1").count()
    if dup_count > 0:
        print(f"⚠️ Found {dup_count} duplicate rows for keys {key_cols}")
    else:
        print("✅ No duplicate keys found.")
    return df.dropDuplicates(key_cols)

def data_quality_summary(df: DataFrame, table_name: str):
    print(f"\n===== Data Quality Report for {table_name} =====")
    df.printSchema()
    print("Row Count:", df.count())
    print("Null Percentage:")
    null_percentage(df).show(truncate=False)


# ------------------------------------------------
# 2) AUDIT / METADATA
# ------------------------------------------------
def add_audit_columns(df: DataFrame, source_name: str) -> DataFrame:
    return (df
        .withColumn("created_at", F.current_timestamp())
        .withColumn("source_system", F.lit(source_name))
        .withColumn("record_hash",
                    F.sha2(F.concat_ws("||", *[F.col(c).cast("string") for c in df.columns]), 256))
    )


# ------------------------------------------------
# 3) QUARANTINE (local path based, schema-stable)
# ------------------------------------------------
def quarantine(df: DataFrame, code: str, table_label: str, paths_silver: dict):
    """
    Schema-stable quarantine sink: stores payload JSON + envelope cols.
    """
    if df is None:
        return

    qpath = f"{paths_silver['_quarantine']}/{table_label}/{code}"

    qt = (df
          .withColumn("_quarantine_code",  F.lit(code))
          .withColumn("_quarantine_table", F.lit(table_label))
          .withColumn("_quarantine_ts",    F.current_timestamp())
          .withColumn("payload",           F.to_json(F.struct(*[F.col(c) for c in df.columns])))
          .select("_quarantine_code","_quarantine_table","_quarantine_ts","payload"))

    (qt.write
       .format("delta")
       .mode("append")
       .save(qpath))

    print(f"[QUARANTINE] {code} → {qpath} (rows={qt.count()})")


# ------------------------------------------------
# 4) DEDUPE / NORMALIZE / DATES
# ------------------------------------------------
def drop_dupes_keep_latest(df: DataFrame, key_cols: list, order_desc_cols: list) -> DataFrame:
    """
    Window dedupe: latest record wins per business key.
    """
    w = W.partitionBy(*key_cols).orderBy(*[F.desc(c) for c in order_desc_cols])
    return (df.withColumn("_rn", F.row_number().over(w))
              .filter(F.col("_rn") == 1)
              .drop("_rn"))

def normalize_categories(df: DataFrame) -> DataFrame:
    """
    Normalize common categorical cols if present.
    """
    d = df
    if "Gender" in d.columns:
        d = d.withColumn(
            "Gender",
            F.when(F.lower(F.col("Gender")).isin("m","male"), "M")
             .when(F.lower(F.col("Gender")).isin("f","female"), "F")
             .otherwise(F.col("Gender"))
        )
    if "Smoker" in d.columns:
        d = d.withColumn(
            "Smoker",
            F.when(F.lower(F.col("Smoker")).isin("y","yes","1"), "Y")
             .when(F.lower(F.col("Smoker")).isin("n","no","0"), "N")
             .otherwise(F.col("Smoker"))
        )
    return d

def fix_dates(df: DataFrame, start_col: str, end_col: str) -> DataFrame:
    """
    Swap reversed dates safely.
    """
    return (df
      .withColumn("_start", F.col(start_col))
      .withColumn("_end",   F.col(end_col))
      .withColumn("_swap",  (F.col("_end") < F.col("_start")))
      .withColumn(start_col, F.when(F.col("_swap"), F.col("_end")).otherwise(F.col("_start")))
      .withColumn(end_col,   F.when(F.col("_swap"), F.col("_start")).otherwise(F.col("_end")))
      .drop("_start","_end","_swap"))


# ------------------------------------------------
# 5) NULL HANDLING
# ------------------------------------------------
def impute_zero(df: DataFrame, colname: str) -> DataFrame:
    return df.withColumn(colname, F.when(F.col(colname).isNull(), F.lit(0.0)).otherwise(F.col(colname)))

def fill_with_mode(df: DataFrame, colname: str) -> DataFrame:
    mode_val = df.groupBy(colname).count().orderBy(F.desc("count")).first()
    if mode_val and mode_val[0] is not None:
        return df.fillna({colname: mode_val[0]})
    return df


# ------------------------------------------------
# 6) FK VALIDATION
# ------------------------------------------------
def fk_filter(df: DataFrame, fk_col: str, ref_df: DataFrame, ref_key: str,
              table_label: str, reason: str, paths_silver: dict):
    """
    Quarantine FK orphans and return only valid rows.
    """
    ref = ref_df.select(F.col(ref_key).alias("_ref")).dropDuplicates()
    joined = df.join(ref, df[fk_col] == F.col("_ref"), "left")
    bad = joined.filter(F.col("_ref").isNull()).drop("_ref")
    good = joined.filter(F.col("_ref").isNotNull()).drop("_ref")

    if bad.take(1):
        quarantine(bad, reason, table_label, paths_silver)

    return good


# ------------------------------------------------
# 7) DQ RULES (EXPECT + REF)
# ------------------------------------------------
def dq_expect(df: DataFrame, name: str, expr: str, severity: str,
              table_label: str, paths_silver: dict):
    """
    Evaluate boolean SQL expression on DF.
    Quarantine failures; raise if severity='error'.
    """
    total = df.count()
    bad = df.filter(f"NOT ({expr})")
    bad_cnt = bad.count()

    if bad_cnt > 0:
        pct = round(bad_cnt / max(total,1) * 100.0, 4)
        print(f"❌ DQ FAIL [{table_label}] {name}: {bad_cnt}/{total} ({pct}%)")
        quarantine(bad, name, table_label, paths_silver)

        if severity.lower() == "error":
            raise Exception(f"DQ gate failed: {table_label} · {name}")
    else:
        print(f"✅ DQ PASS [{table_label}] {name}")

def dq_left_anti_ref(df: DataFrame, ref_df: DataFrame, key_col: str, ref_col: str,
                     name: str, severity: str, table_label: str, paths_silver: dict):
    """
    Validate df[key_col] exists in ref_df[ref_col]
    """
    ref = ref_df.select(F.col(ref_col).alias("_ref_key")).dropDuplicates()
    bad = df.join(ref, F.col(key_col) == F.col("_ref_key"), "left_anti")

    bad_cnt = bad.count()
    total = df.count()

    if bad_cnt > 0:
        pct = round(bad_cnt / max(total,1) * 100.0, 4)
        print(f"❌ DQ FAIL [{table_label}] {name}: {bad_cnt}/{total} ({pct}%) missing in reference")
        quarantine(bad, name, table_label, paths_silver)

        if severity.lower() == "error":
            raise Exception(f"DQ gate failed: {table_label} · {name}")
    else:
        print(f"✅ DQ PASS [{table_label}] {name}")


# ------------------------------------------------
# 8) METRICS (delta path)
# ------------------------------------------------
def write_metric(spark, name: str, value, context: str, paths_silver: dict):
    mdf = spark.createDataFrame(
        [(name, str(value), context, datetime.utcnow())],
        "metric STRING, value STRING, context STRING, ts TIMESTAMP"
    )

    (
        mdf.write
        .format("delta")
        .mode("append")
        .save(paths_silver["_metrics"])
    )

    print(f"[METRIC] {name}={value} ctx={context}")



print("✅ utils_silver.py loaded")
