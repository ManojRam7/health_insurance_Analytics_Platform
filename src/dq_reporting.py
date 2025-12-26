# Data Quality Reporting Module
# Phase 4: Comprehensive DQ metrics, quality dashboards, trend analysis

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import statistics

PROJECT_ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ColumnQualityMetrics:
    """Quality metrics for a column"""
    column_name: str
    data_type: str
    total_records: int
    null_count: int
    null_percent: float
    unique_count: int
    unique_percent: float
    min_value: Any
    max_value: Any
    mean_value: float
    stddev_value: float
    completeness_score: float  # 0-100
    validity_score: float      # 0-100
    
    def to_dict(self):
        return asdict(self)

@dataclass
class TableQualityMetrics:
    """Quality metrics for a table"""
    table_name: str
    record_count: int
    column_count: int
    timestamp: str
    columns: List[Dict[str, Any]]
    overall_completeness: float  # 0-100
    overall_validity: float      # 0-100
    overall_quality_score: float  # 0-100
    freshness_hours: float
    issues: List[str]
    warnings: List[str]
    
    def to_dict(self):
        return asdict(self)

@dataclass
@dataclass
class PipelineQualityReport:
    """Complete quality report for pipeline"""
    generated_at: str
    total_tables: int
    tables: Dict[str, Dict[str, Any]]
    pipeline_quality_score: float  # Average of all tables
    critical_issues: List[str]
    warnings: List[str]
    trends: Dict[str, Any]  # Quality trends over time
    
    def to_dict(self):
        return asdict(self)

# ============================================================================
# DATA QUALITY CHECKER
# ============================================================================

class DataQualityChecker:
    """Comprehensive data quality analysis"""
    
    def __init__(self, spark_session=None):
        """Initialize quality checker"""
        self.spark = spark_session
        self.quality_reports = []
        self.output_dir = PROJECT_ROOT / "logs" / "dq_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def check_table_quality(self, table_name: str, df=None) -> TableQualityMetrics:
        """Comprehensive quality check for a table"""
        
        # Note: This is a template. In production, would use actual Spark DataFrame
        logger.info(f"Checking quality for table: {table_name}")
        
        # Simulated metrics (in production, compute from actual data)
        record_count = 1000  # Would be df.count()
        column_count = 15
        
        column_metrics = []
        completeness_scores = []
        validity_scores = []
        
        issues = []
        warnings = []
        
        # Simulate column checks
        for i in range(column_count):
            col_name = f"column_{i}"
            null_count = 5 if i % 3 == 0 else 0
            null_percent = (null_count / record_count) * 100
            completeness = 100 - null_percent
            
            col_metric = ColumnQualityMetrics(
                column_name=col_name,
                data_type="STRING",
                total_records=record_count,
                null_count=null_count,
                null_percent=null_percent,
                unique_count=record_count - null_count,
                unique_percent=((record_count - null_count) / record_count) * 100,
                min_value=None,
                max_value=None,
                mean_value=0.0,
                stddev_value=0.0,
                completeness_score=completeness,
                validity_score=95.0
            )
            
            column_metrics.append(col_metric.to_dict())
            completeness_scores.append(completeness)
            validity_scores.append(95.0)
            
            # Flag issues
            if null_percent > 10:
                issues.append(f"{col_name}: High null rate ({null_percent:.1f}%)")
            elif null_percent > 5:
                warnings.append(f"{col_name}: Moderate null rate ({null_percent:.1f}%)")
        
        overall_completeness = statistics.mean(completeness_scores) if completeness_scores else 100
        overall_validity = statistics.mean(validity_scores) if validity_scores else 100
        overall_score = (overall_completeness + overall_validity) / 2
        
        table_metric = TableQualityMetrics(
            table_name=table_name,
            record_count=record_count,
            column_count=column_count,
            timestamp=datetime.now().isoformat(),
            columns=column_metrics,
            overall_completeness=overall_completeness,
            overall_validity=overall_validity,
            overall_quality_score=overall_score,
            freshness_hours=0.1,  # Would calculate from metadata
            issues=issues,
            warnings=warnings
        )
        
        self.quality_reports.append(table_metric)
        
        logger.info(f"  Quality Score: {overall_score:.1f}/100")
        logger.info(f"  Issues: {len(issues)}, Warnings: {len(warnings)}")
        
        return table_metric
    
    def check_referential_integrity(self, parent_table: str, child_table: str,
                                   parent_key: str, child_key: str) -> Dict[str, Any]:
        """Check referential integrity between tables"""
        
        logger.info(f"Checking referential integrity: {child_table}.{child_key} → "
                   f"{parent_table}.{parent_key}")
        
        # Simulated result
        result = {
            "parent_table": parent_table,
            "child_table": child_table,
            "parent_key": parent_key,
            "child_key": child_key,
            "child_records": 1000,
            "matching_records": 995,
            "orphaned_records": 5,
            "orphan_percent": 0.5,
            "status": "PASS" if 0.5 < 1.0 else "FAIL",  # Threshold: 1% orphans
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"  Orphaned records: {result['orphaned_records']} "
                   f"({result['orphan_percent']:.2f}%)")
        
        return result
    
    def check_distribution_stats(self, table_name: str, numeric_columns: List[str]) -> Dict[str, Any]:
        """Check distribution statistics for numeric columns"""
        
        logger.info(f"Checking distribution stats for {table_name}")
        
        dist_stats = {}
        for col in numeric_columns:
            dist_stats[col] = {
                "min": 0.0,
                "max": 1000.0,
                "mean": 500.0,
                "median": 450.0,
                "stddev": 150.0,
                "p10": 100.0,
                "p25": 250.0,
                "p75": 750.0,
                "p90": 900.0,
                "skewness": 0.2,  # Slight right skew
                "kurtosis": 0.5,
                "outliers_count": 5
            }
        
        return dist_stats
    
    def generate_pipeline_report(self, tables_to_check: List[str]) -> PipelineQualityReport:
        """Generate comprehensive pipeline quality report"""
        
        logger.info("Generating pipeline quality report...")
        
        critical_issues = []
        warnings = []
        table_reports = {}
        quality_scores = []
        
        for table_name in tables_to_check:
            try:
                table_metric = self.check_table_quality(table_name)
                table_reports[table_name] = table_metric.to_dict()
                quality_scores.append(table_metric.overall_quality_score)
                
                # Collect issues and warnings
                critical_issues.extend([f"{table_name}: {issue}" 
                                       for issue in table_metric.issues])
                warnings.extend([f"{table_name}: {warning}" 
                               for warning in table_metric.warnings])
            
            except Exception as e:
                critical_issues.append(f"{table_name}: Error during check - {str(e)}")
        
        pipeline_score = statistics.mean(quality_scores) if quality_scores else 0
        
        # Simulate trends
        trends = {
            "quality_trend": "improving" if pipeline_score > 80 else "degrading",
            "improvement_rate": 2.5,  # % improvement per day
            "days_to_critical": None if pipeline_score > 70 else 3,
            "recent_changes": [
                "Members table completeness: 98.5% → 99.2%",
                "Claims table validity: 96.0% → 95.8%"
            ]
        }
        
        report = PipelineQualityReport(
            generated_at=datetime.now().isoformat(),
            total_tables=len(table_reports),
            tables=table_reports,
            pipeline_quality_score=pipeline_score,
            critical_issues=critical_issues,
            warnings=warnings,
            trends=trends
        )
        
        return report
    
    def save_report(self, report: PipelineQualityReport, filename: str = None):
        """Save DQ report to JSON"""
        filename = filename or f"dq_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = self.output_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"DQ report saved to {output_path}")
        return output_path
    
    def print_report(self, report: PipelineQualityReport):
        """Print DQ report to console"""
        print("\n" + "="*100)
        print("DATA QUALITY REPORT")
        print("="*100)
        print(f"Generated: {report.generated_at}")
        print(f"Pipeline Quality Score: {report.pipeline_quality_score:.1f}/100")
        print(f"Total Tables: {report.total_tables}")
        
        print("\nTABLE QUALITY:")
        print("-"*100)
        print(f"{'Table':<30} {'Records':<15} {'Completeness':<15} {'Validity':<15} {'Overall Score':<15}")
        print("-"*100)
        
        for table_name, metrics_dict in report.tables.items():
            completeness = metrics_dict.get('completeness', 0)
            validity = metrics_dict.get('validity', 0)
            overall = metrics_dict.get('overall_score', 0)
            records = metrics_dict.get('record_count', 0)
            print(f"{table_name:<30} {records:<15} "
                  f"{completeness:<14.1f}% {validity:<14.1f}% "
                  f"{overall:<14.1f}%")
        
        print("-"*100)
        
        if report.critical_issues:
            print("\nCRITICAL ISSUES:")
            for issue in report.critical_issues:
                print(f"  ❌ {issue}")
        
        if report.warnings:
            print("\nWARNINGS:")
            for warning in report.warnings:
                print(f"  ⚠️  {warning}")
        
        print("\nTRENDS:")
        print(f"  Trend: {report.trends['quality_trend']}")
        print(f"  Improvement Rate: {report.trends['improvement_rate']:.1f}% per day")
        
        print("="*100 + "\n")

# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_dq_checker = None

def get_dq_checker(spark_session=None) -> DataQualityChecker:
    """Get or create DQ checker instance"""
    global _dq_checker
    if _dq_checker is None:
        _dq_checker = DataQualityChecker(spark_session)
    return _dq_checker


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """Run DQ reporting standalone"""
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*100)
    print("🔍 DATA QUALITY REPORTING - PHASE 4")
    print("="*100)
    
    try:
        # Initialize DQ checker
        dq = get_dq_checker()
        print("✅ DQ Checker initialized")
        
        # Generate sample report (would normally use actual data)
        report = PipelineQualityReport(
            generated_at=datetime.now().isoformat(),
            total_tables=3,
            tables={
                "bronze_policies": {
                    "record_count": 100000,
                    "completeness": 95.5,
                    "validity": 98.2,
                    "overall_score": 96.9
                },
                "silver_claims": {
                    "record_count": 250000,
                    "completeness": 97.8,
                    "validity": 99.1,
                    "overall_score": 98.5
                },
                "gold_features": {
                    "record_count": 150000,
                    "completeness": 99.2,
                    "validity": 99.8,
                    "overall_score": 99.5
                }
            },
            pipeline_quality_score=98.3,
            critical_issues=[],
            warnings=["Minor schema drift detected in claims table"],
            trends={
                "quality_trend": "IMPROVING",
                "improvement_rate": 0.5
            }
        )
        
        # Print report to console
        dq.print_report(report)
        
        # Save report with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"dq_report_{timestamp}.json"
        output_path = dq.save_report(report, filename=filename)
        print(f"✅ Report saved to: {output_path}")
        
        print("\n📊 DQ Reporting Complete!")
        print("="*100 + "\n")
        
    except Exception as e:
        print(f"❌ Error running DQ reporting: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
