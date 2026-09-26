# ML utilities for the health insurance pipeline
# Provides reusable functions for model training, evaluation, and serving

import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any
from pathlib import Path

import mlflow
import mlflow.pyspark.ml
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, when, mean, stddev, monotonically_increasing_id
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.mllib.evaluation import MulticlassMetrics, BinaryClassificationMetrics
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

logger = logging.getLogger(__name__)


class MLPipeline:
    """
    Encapsulates ML model training, evaluation, and deployment logic.
    Handles feature engineering, model selection, and model versioning.
    """
    
    def __init__(self, 
                 spark: SparkSession,
                 experiment_name: str,
                 use_case: str,
                 config: Dict[str, Any]):
        """
        Initialize ML pipeline.
        
        Args:
            spark: SparkSession object
            experiment_name: MLflow experiment name
            use_case: Use case identifier (e.g., 'policy_churn')
            config: Configuration dict from config.py
        """
        self.spark = spark
        self.experiment_name = experiment_name
        self.use_case = use_case
        self.config = config
        self.ml_config = config.get("ML_CONFIG", {})
        
        # Set MLflow experiment
        mlflow.set_experiment(experiment_name)
        
        logger.info(f"MLPipeline initialized for use case: {use_case}")
    
    def handle_nulls(self, 
                     df: DataFrame, 
                     numeric_cols: List[str], 
                     categorical_cols: List[str],
                     null_strategy: Dict[str, Any]) -> DataFrame:
        """
        Handle null values in features.
        
        Args:
            df: Input DataFrame
            numeric_cols: List of numeric column names
            categorical_cols: List of categorical column names
            null_strategy: Dict with 'numeric' and 'categorical' strategies
        
        Returns:
            DataFrame with nulls handled
        """
        numeric_fill = null_strategy.get("numeric", 0.0)
        categorical_fill = null_strategy.get("categorical", "Unknown")
        
        # Fill numeric columns
        for col_name in numeric_cols:
            if col_name in df.columns:
                df = df.fillna({col_name: numeric_fill})
        
        # Fill categorical columns
        for col_name in categorical_cols:
            if col_name in df.columns:
                df = df.fillna({col_name: categorical_fill})
        
        logger.info(f"Null handling complete: numeric→{numeric_fill}, categorical→{categorical_fill}")
        return df
    
    def create_feature_pipeline(self,
                               numeric_features: List[str],
                               categorical_features: List[str]) -> Pipeline:
        """
        Create feature engineering pipeline with indexing, encoding, and assembly.
        
        Args:
            numeric_features: List of numeric column names
            categorical_features: List of categorical column names
        
        Returns:
            PySpark Pipeline for feature transformation
        """
        stages = []
        
        # Index categorical features
        indexed_cat_features = []
        for cat_col in categorical_features:
            indexer = StringIndexer(
                inputCol=cat_col,
                outputCol=f"{cat_col}_indexed",
                handleInvalid="keep"
            )
            stages.append(indexer)
            indexed_cat_features.append(f"{cat_col}_indexed")
        
        # One-hot encode indexed categorical features
        encoded_cat_features = []
        for indexed_col in indexed_cat_features:
            encoder = OneHotEncoder(
                inputCol=indexed_col,
                outputCol=f"{indexed_col}_encoded",
                dropLast=True,
                handleInvalid="keep"
            )
            stages.append(encoder)
            encoded_cat_features.append(f"{indexed_col}_encoded")
        
        # Assemble all features into vector
        all_features = numeric_features + encoded_cat_features
        assembler = VectorAssembler(
            inputCols=all_features,
            outputCol="features",
            handleInvalid="keep"
        )
        stages.append(assembler)
        
        pipeline = Pipeline(stages=stages)
        logger.info(f"Feature pipeline created with {len(numeric_features)} numeric + {len(categorical_features)} categorical features")
        
        return pipeline
    
    def compute_class_weights(self, df: DataFrame, label_col: str) -> Dict[int, float]:
        """
        Compute class weights for imbalanced classification.
        
        Args:
            df: Training DataFrame
            label_col: Name of label column
        
        Returns:
            Dict mapping class label to weight
        """
        label_counts = df.groupBy(label_col).count().collect()
        total = df.count()
        
        class_weights = {}
        for row in label_counts:
            label = int(row[label_col])
            count = row["count"]
            weight = total / (len(label_counts) * count)  # Inverse frequency weighting
            class_weights[label] = weight
        
        logger.info(f"Computed class weights: {class_weights}")
        return class_weights
    
    def create_stratified_split(self,
                                df: DataFrame,
                                label_col: str,
                                train_ratio: float = 0.8,
                                seed: int = 42) -> Tuple[DataFrame, DataFrame]:
        """
        Create stratified train/test split (maintains label distribution).
        
        Args:
            df: Input DataFrame
            label_col: Name of label column
            train_ratio: Fraction for training (0-1)
            seed: Random seed
        
        Returns:
            Tuple of (train_df, test_df)
        """
        # Get class distribution
        label_values = df.select(label_col).distinct().rdd.flatMap(lambda x: x).collect()
        
        # Compute fractions for stratified split
        fractions = {}
        for label in label_values:
            fractions[label] = train_ratio
        
        # Perform stratified split
        train_df = df.sampleBy(label_col, fractions, seed=seed)
        test_df = df.subtract(train_df)  # Ensure no overlap
        
        train_count = train_df.count()
        test_count = test_df.count()
        
        logger.info(f"Stratified split: {train_count} train ({100*train_count/(train_count+test_count):.1f}%), "
                   f"{test_count} test ({100*test_count/(train_count+test_count):.1f}%)")
        
        return train_df, test_df
    
    def evaluate_model(self,
                      predictions: DataFrame,
                      label_col: str = "label",
                      pred_col: str = "prediction",
                      prob_col: str = "probability") -> Dict[str, float]:
        """
        Evaluate binary classification model.
        
        Args:
            predictions: DataFrame with predictions and labels
            label_col: Name of label column
            pred_col: Name of prediction column
            prob_col: Name of probability column
        
        Returns:
            Dict with evaluation metrics
        """
        evaluator_roc = BinaryClassificationEvaluator(
            labelCol=label_col,
            rawPredictionCol=prob_col,
            metricName="areaUnderROC"
        )
        auc_roc = evaluator_roc.evaluate(predictions)
        
        evaluator_pr = BinaryClassificationEvaluator(
            labelCol=label_col,
            rawPredictionCol=prob_col,
            metricName="areaUnderPR"
        )
        auc_pr = evaluator_pr.evaluate(predictions)
        
        evaluator_accuracy = MulticlassClassificationEvaluator(
            labelCol=label_col,
            predictionCol=pred_col,
            metricName="accuracy"
        )
        accuracy = evaluator_accuracy.evaluate(predictions)
        
        evaluator_f1 = MulticlassClassificationEvaluator(
            labelCol=label_col,
            predictionCol=pred_col,
            metricName="f1"
        )
        f1 = evaluator_f1.evaluate(predictions)
        
        evaluator_precision = MulticlassClassificationEvaluator(
            labelCol=label_col,
            predictionCol=pred_col,
            metricName="weightedPrecision"
        )
        precision = evaluator_precision.evaluate(predictions)
        
        evaluator_recall = MulticlassClassificationEvaluator(
            labelCol=label_col,
            predictionCol=pred_col,
            metricName="weightedRecall"
        )
        recall = evaluator_recall.evaluate(predictions)
        
        metrics = {
            "auc_roc": auc_roc,
            "auc_pr": auc_pr,
            "accuracy": accuracy,
            "f1": f1,
            "precision": precision,
            "recall": recall,
        }
        
        logger.info(f"Model Evaluation - AUC ROC: {auc_roc:.4f}, AUC PR: {auc_pr:.4f}, F1: {f1:.4f}")
        
        return metrics
    
    def get_feature_importance(self,
                              model: Any,
                              feature_names: List[str],
                              top_n: int = 10) -> Dict[str, float]:
        """
        Extract feature importance from tree-based models.
        
        Args:
            model: Trained ML model
            feature_names: List of feature names
            top_n: Number of top features to return
        
        Returns:
            Dict mapping feature name to importance
        """
        try:
            # For RandomForest and GBT models
            importances = model.featureImportances.toArray()
            feature_importance = dict(zip(feature_names, importances))
            
            # Sort by importance and return top-n
            top_features = dict(sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n])
            
            logger.info(f"Top {top_n} features: {list(top_features.keys())}")
            return top_features
        except AttributeError:
            logger.warning("Feature importance not available for this model type")
            return {}
    
    def log_to_mlflow(self,
                     params: Dict[str, Any],
                     metrics: Dict[str, float],
                     model: Any = None,
                     artifact_path: str = "model",
                     feature_importance: Dict[str, float] = None):
        """
        Log parameters, metrics, model, and artifacts to MLflow.
        
        Args:
            params: Model parameters
            metrics: Evaluation metrics
            model: Trained model object
            artifact_path: Path for artifact storage
            feature_importance: Feature importance dict
        """
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        
        # Log feature importance if available
        if feature_importance:
            for feature, importance in feature_importance.items():
                mlflow.log_metric(f"feature_importance_{feature}", importance)
        
        # Log model
        if model:
            mlflow.pyspark.ml.log_model(
                model,
                artifact_path=artifact_path,
                registered_model_name=self.experiment_name
            )
        
        logger.info(f"Logged to MLflow - params: {len(params)}, metrics: {len(metrics)}")
    
    def save_model(self, model: Any, path: str):
        """
        Save model to ADLS.
        
        Args:
            model: Trained model
            path: ADLS path
        """
        model.save(path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str) -> PipelineModel:
        """
        Load model from ADLS.
        
        Args:
            path: ADLS path
        
        Returns:
            Loaded PipelineModel
        """
        model = PipelineModel.load(path)
        logger.info(f"Model loaded from {path}")
        return model


class DataDriftDetector:
    """
    Detects data drift in features between training and scoring distributions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize drift detector with config."""
        self.config = config.get("DATA_DRIFT", {})
        self.enabled = self.config.get("enabled", False)
        self.kl_threshold = self.config.get("kl_divergence_threshold", 0.2)
        self.max_shift_pct = self.config.get("max_feature_shift_pct", 20)
    
    def compute_kl_divergence(self, train_stats: Dict, score_stats: Dict) -> float:
        """
        Compute KL divergence between two distributions (simplified).
        
        Args:
            train_stats: Training data statistics
            score_stats: Scoring data statistics
        
        Returns:
            KL divergence metric
        """
        import math
        kl_sum = 0
        
        for key in train_stats:
            if key in score_stats:
                train_mean = train_stats[key].get("mean", 0)
                score_mean = score_stats[key].get("mean", 0)
                
                if train_mean > 0:
                    kl_sum += abs(score_mean - train_mean) / train_mean
        
        return min(kl_sum / len(train_stats), 1.0)  # Normalize
    
    def detect_drift(self,
                    train_df: DataFrame,
                    score_df: DataFrame,
                    feature_cols: List[str]) -> Dict[str, Any]:
        """
        Detect data drift in features.
        
        Args:
            train_df: Training DataFrame
            score_df: Scoring DataFrame
            feature_cols: Feature column names
        
        Returns:
            Dict with drift detection results
        """
        if not self.enabled:
            return {"drift_detected": False, "reason": "Drift detection disabled"}
        
        train_stats = {}
        score_stats = {}
        
        for col_name in feature_cols:
            try:
                # Compute mean and stddev for numeric columns
                train_row = train_df.select(
                    mean(col_name).alias("mean"),
                    stddev(col_name).alias("stddev")
                ).collect()[0]
                
                score_row = score_df.select(
                    mean(col_name).alias("mean"),
                    stddev(col_name).alias("stddev")
                ).collect()[0]
                
                train_stats[col_name] = {
                    "mean": float(train_row["mean"] or 0),
                    "stddev": float(train_row["stddev"] or 0)
                }
                score_stats[col_name] = {
                    "mean": float(score_row["mean"] or 0),
                    "stddev": float(score_row["stddev"] or 0)
                }
            except Exception as e:
                logger.debug(f"Could not compute stats for {col_name}: {e}")
                continue
        
        # Compute KL divergence
        kl_div = self.compute_kl_divergence(train_stats, score_stats)
        drift_detected = kl_div > self.kl_threshold
        
        result = {
            "drift_detected": drift_detected,
            "kl_divergence": kl_div,
            "threshold": self.kl_threshold,
            "train_stats": train_stats,
            "score_stats": score_stats,
        }
        
        if drift_detected:
            logger.warning(f"DATA DRIFT DETECTED: KL divergence {kl_div:.4f} > {self.kl_threshold}")
        else:
            logger.info(f"No data drift detected (KL divergence: {kl_div:.4f})")
        
        return result


# Logging setup
def setup_logging(config: Dict[str, Any]):
    """Configure logging."""
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
