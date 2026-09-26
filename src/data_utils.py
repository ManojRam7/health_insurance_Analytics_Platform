# Data utilities for the health insurance pipeline
# Provides reusable functions for data quality, validation, and transformation

import logging
from typing import Dict, List, Tuple, Any
from datetime import datetime

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql.functions import (
    col, count, when, isnan, isnull, max as spark_max, min as spark_min,
    avg, stddev, lit, row_number
)

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """
    Validates data quality against configured thresholds.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data quality validator.
        
        Args:
            config: Configuration dict from config.py
        """
        self.config = config.get("DATA_QUALITY_THRESHOLDS", {})
        logger.info("DataQualityValidator initialized")
    
    def check_nulls(self,
                   df: DataFrame,
                   table_name: str,
                   threshold_pct: float = None) -> Dict[str, float]:
        """
        Check null percentages for all columns.
        
        Args:
            df: DataFrame to check
            table_name: Name of table (for config lookup)
            threshold_pct: Max allowed null percentage (uses config if None)
        
        Returns:
            Dict mapping column name to null percentage
        """
        total_rows = df.count()
        if total_rows == 0:
            logger.warning(f"{table_name} is empty!")
            return {}
        
        if threshold_pct is None:
            threshold_pct = self.config.get(table_name, {}).get("max_null_pct", 20)
        
        null_counts = df.select([
            (count(when(isnull(col_name) | isnan(col_name), col_name)) / total_rows * 100)
            .alias(col_name)
            for col_name in df.columns
        ]).collect()[0]
        
        null_dict = {col: float(null_counts[col]) for col in df.columns}
        
        # Check against threshold
        violations = {col: pct for col, pct in null_dict.items() if pct > threshold_pct}
        
        if violations:
            logger.warning(f"{table_name} - Null threshold violations: {violations}")
        else:
            logger.info(f"{table_name} - Null check passed (all < {threshold_pct}%)")
        
        return null_dict
    
    def check_numeric_range(self,
                           df: DataFrame,
                           table_name: str,
                           column_ranges: Dict[str, Tuple[float, float]]) -> Dict[str, Dict]:
        """
        Check numeric columns are within expected ranges.
        
        Args:
            df: DataFrame to check
            table_name: Name of table
            column_ranges: Dict mapping column name to (min, max) tuple
        
        Returns:
            Dict with range check results
        """
        results = {}
        
        for col_name, (min_val, max_val) in column_ranges.items():
            if col_name not in df.columns:
                logger.warning(f"Column {col_name} not found in {table_name}")
                continue
            
            stats = df.select(
                spark_min(col_name).alias("min"),
                spark_max(col_name).alias("max"),
                count(when((col(col_name) < min_val) | (col(col_name) > max_val), 1))
                .alias("out_of_range_count")
            ).collect()[0]
            
            out_of_range = stats["out_of_range_count"]
            actual_min = float(stats["min"] or min_val)
            actual_max = float(stats["max"] or max_val)
            
            results[col_name] = {
                "expected_range": (min_val, max_val),
                "actual_range": (actual_min, actual_max),
                "out_of_range_count": out_of_range,
                "in_range": out_of_range == 0
            }
            
            status = "" if out_of_range == 0 else ""
            logger.info(f"{status} {table_name}.{col_name}: {actual_min:.2f}-{actual_max:.2f} "
                       f"(expected: {min_val}-{max_val}, out-of-range: {out_of_range})")
        
        return results
    
    def check_categorical_values(self,
                                df: DataFrame,
                                table_name: str,
                                column_values: Dict[str, List[str]]) -> Dict[str, Dict]:
        """
        Check categorical columns contain only expected values.
        
        Args:
            df: DataFrame to check
            table_name: Name of table
            column_values: Dict mapping column to list of allowed values
        
        Returns:
            Dict with categorical check results
        """
        results = {}
        
        for col_name, allowed_values in column_values.items():
            if col_name not in df.columns:
                logger.warning(f"Column {col_name} not found in {table_name}")
                continue
            
            distinct_values = df.select(col_name).distinct().rdd.flatMap(lambda x: x).collect()
            unexpected_values = [v for v in distinct_values if v not in allowed_values and v is not None]
            
            results[col_name] = {
                "allowed_values": allowed_values,
                "actual_values": distinct_values,
                "unexpected_values": unexpected_values,
                "valid": len(unexpected_values) == 0
            }
            
            status = "" if len(unexpected_values) == 0 else ""
            logger.info(f"{status} {table_name}.{col_name}: {len(distinct_values)} distinct values "
                       f"(unexpected: {unexpected_values})")
        
        return results
    
    def check_duplicate_rows(self, df: DataFrame, table_name: str, key_cols: List[str] = None) -> Dict:
        """
        Check for duplicate rows.
        
        Args:
            df: DataFrame to check
            table_name: Name of table
            key_cols: Columns to check for duplicates (all if None)
        
        Returns:
            Dict with duplicate check results
        """
        if key_cols is None:
            key_cols = df.columns
        
        total_rows = df.count()
        distinct_rows = df.select(key_cols).distinct().count()
        duplicates = total_rows - distinct_rows
        
        result = {
            "total_rows": total_rows,
            "distinct_rows": distinct_rows,
            "duplicate_rows": duplicates,
            "no_duplicates": duplicates == 0
        }
        
        status = "" if duplicates == 0 else ""
        logger.info(f"{status} {table_name} - Duplicates: {duplicates}/{total_rows}")
        
        return result
    
    def generate_report(self, df: DataFrame, table_name: str) -> Dict[str, Any]:
        """
        Generate comprehensive data quality report.
        
        Args:
            df: DataFrame to analyze
            table_name: Name of table
        
        Returns:
            Dict with complete quality report
        """
        report = {
            "table_name": table_name,
            "timestamp": datetime.now().isoformat(),
            "row_count": df.count(),
            "column_count": len(df.columns),
            "columns": df.columns,
        }
        
        logger.info(f"Data Quality Report: {table_name} ({report['row_count']} rows, "
                   f"{report['column_count']} columns)")
        
        return report


class DataTransformer:
    """
    Handles data transformations and feature engineering.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize transformer."""
        self.config = config
    
    def apply_outlier_removal(self,
                             df: DataFrame,
                             column: str,
                             method: str = "iqr",
                             threshold: float = 1.5) -> DataFrame:
        """
        Remove outliers using IQR or standard deviation method.
        
        Args:
            df: Input DataFrame
            column: Column name
            method: "iqr" or "stddev"
            threshold: IQR multiplier (1.5) or stddev multiplier (3)
        
        Returns:
            DataFrame with outliers removed
        """
        if method == "iqr":
            q1 = df.approxQuantile(column, [0.25], 0.01)[0]
            q3 = df.approxQuantile(column, [0.75], 0.01)[0]
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            
            df_clean = df.filter((col(column) >= lower_bound) & (col(column) <= upper_bound))
            removed = df.count() - df_clean.count()
            logger.info(f"IQR outlier removal: {removed} rows removed from {column}")
            
        elif method == "stddev":
            mean_val = df.agg(avg(column)).collect()[0][0]
            std_val = df.agg(stddev(column)).collect()[0][0]
            lower_bound = mean_val - threshold * std_val
            upper_bound = mean_val + threshold * std_val
            
            df_clean = df.filter((col(column) >= lower_bound) & (col(column) <= upper_bound))
            removed = df.count() - df_clean.count()
            logger.info(f"StdDev outlier removal: {removed} rows removed from {column}")
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return df_clean
    
    def create_interaction_features(self,
                                   df: DataFrame,
                                   feature_pairs: List[Tuple[str, str]]) -> DataFrame:
        """
        Create interaction features from numeric columns.
        
        Args:
            df: Input DataFrame
            feature_pairs: List of (col1, col2) tuples to interact
        
        Returns:
            DataFrame with interaction features added
        """
        for col1, col2 in feature_pairs:
            interaction_col = f"{col1}_x_{col2}"
            df = df.withColumn(interaction_col, col(col1) * col(col2))
            logger.debug(f"Created interaction feature: {interaction_col}")
        
        logger.info(f"Created {len(feature_pairs)} interaction features")
        return df
    
    def create_binned_features(self,
                              df: DataFrame,
                              column: str,
                              bins: List[float]) -> DataFrame:
        """
        Create binned/bucketed feature from numeric column.
        
        Args:
            df: Input DataFrame
            column: Column to bin
            bins: List of bin edges
        
        Returns:
            DataFrame with binned column added
        """
        bin_col = f"{column}_binned"
        
        # Create bins using when/otherwise
        condition = None
        for i, bin_edge in enumerate(bins[:-1]):
            bin_name = f"bin_{i}"
            if condition is None:
                condition = when(col(column) <= bin_edge, lit(bin_name))
            else:
                condition = condition.when(col(column) <= bin_edge, lit(bin_name))
        
        # Default for last bin
        condition = condition.otherwise(f"bin_{len(bins)-1}")
        df = df.withColumn(bin_col, condition)
        
        logger.info(f"Created binned feature: {bin_col} with {len(bins)-1} bins")
        return df
    
    def resample_for_imbalance(self,
                              df: DataFrame,
                              label_col: str,
                              ratio: float = 1.0,
                              method: str = "oversample") -> DataFrame:
        """
        Resample data to handle class imbalance.
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            ratio: Target ratio (minority/majority)
            method: "oversample" or "undersample"
        
        Returns:
            Resampled DataFrame
        """
        # Count samples per class
        label_counts = df.groupBy(label_col).count().collect()
        counts = {int(row[label_col]): row["count"] for row in label_counts}
        
        minority_label = min(counts, key=counts.get)
        majority_label = max(counts, key=counts.get)
        minority_count = counts[minority_label]
        majority_count = counts[majority_label]
        
        if method == "oversample":
            # Oversample minority class
            minority_df = df.filter(col(label_col) == minority_label)
            target_minority = int(majority_count * ratio)
            oversample_factor = target_minority / minority_count
            
            oversampled = minority_df.sample(withReplacement=True, fraction=oversample_factor)
            majority_df = df.filter(col(label_col) == majority_label)
            df_balanced = majority_df.unionByName(oversampled)
            
            logger.info(f"Oversampled {label_col}={minority_label} from {minority_count} "
                       f"to {target_minority} samples")
        
        elif method == "undersample":
            # Undersample majority class
            majority_df = df.filter(col(label_col) == majority_label)
            target_majority = int(minority_count / ratio)
            undersample_fraction = target_majority / majority_count
            
            undersampled = majority_df.sample(withReplacement=False, fraction=undersample_fraction)
            minority_df = df.filter(col(label_col) == minority_label)
            df_balanced = minority_df.unionByName(undersampled)
            
            logger.info(f"Undersampled {label_col}={majority_label} from {majority_count} "
                       f"to {target_majority} samples")
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return df_balanced


class BatchScoringManager:
    """
    Manages batch scoring with incremental writes and versioning.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize batch scoring manager."""
        self.config = config.get("BATCH_SCORING", {})
        self.enabled = self.config.get("enabled", False)
        self.incremental_writes = self.config.get("incremental_writes", True)
        self.write_mode = self.config.get("write_mode", "append")
        self.partition_by = self.config.get("partition_by", [])
    
    def write_scores(self,
                    df: DataFrame,
                    output_path: str,
                    mode: str = None,
                    partition_cols: List[str] = None):
        """
        Write scored predictions to storage with proper mode and partitioning.
        
        Args:
            df: DataFrame with predictions
            output_path: Target path
            mode: Write mode (append/overwrite, uses config if None)
            partition_cols: Columns to partition by (uses config if None)
        """
        if mode is None:
            mode = self.write_mode
        if partition_cols is None:
            partition_cols = self.partition_by
        
        writer = df.write \
            .mode(mode) \
            .format("delta")
        
        if partition_cols:
            writer = writer.partitionBy(partition_cols)
        
        writer.save(output_path)
        logger.info(f"Scored {df.count()} predictions written to {output_path} "
                   f"(mode={mode}, partitions={partition_cols})")
    
    def get_latest_scores(self,
                         df: DataFrame,
                         partition_cols: List[str] = None) -> DataFrame:
        """
        Get the latest scores when using incremental writes with date partitioning.
        
        Args:
            df: Full scored DataFrame
            partition_cols: Partition columns (uses config if None)
        
        Returns:
            DataFrame with only latest partition values
        """
        if partition_cols is None:
            partition_cols = self.partition_by
        
        if not partition_cols:
            return df
        
        # Get rows with max partition values
        window_spec = Window.orderBy([col(c).desc() for c in partition_cols])
        latest_df = df.withColumn("row_num", row_number().over(window_spec)) \
            .filter(col("row_num") == 1) \
            .drop("row_num")
        
        logger.info(f"Retrieved latest scores for partitions: {partition_cols}")
        return latest_df


# Logging setup
def setup_logging(config: Dict[str, Any]):
    """Configure logging for data utilities."""
    log_config = config.get("LOGGING_CONFIG", {})
    log_level = log_config.get("level", "INFO")
    log_file = log_config.get("log_file")
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler(),
        ]
    )
