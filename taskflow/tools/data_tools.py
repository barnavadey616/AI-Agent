"""
Tabular data profiling, anomaly detection, and automated cleaning tools using pandas.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd
import numpy as np
from taskflow.core.tool import tool
from taskflow import config

@tool(name="profile_dataset", description="Profile a CSV or Excel dataset to detect nulls, duplicates, types, and summary statistics.")
def profile_dataset(file_path: str) -> Dict[str, Any]:
    """Analyzes data quality issues in tabular datasets."""
    p = Path(file_path)
    if not p.is_absolute():
        p = config.BASE_DIR / p
    if not p.exists():
        return {"error": f"File '{file_path}' does not exist."}

    try:
        df = pd.read_csv(p) if p.suffix.lower() == ".csv" else pd.read_excel(p)
        
        total_rows = len(df)
        total_cols = len(df.columns)
        null_counts = df.isnull().sum().to_dict()
        duplicate_rows = int(df.duplicated().sum())

        numeric_summary = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            numeric_summary[col] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": round(float(df[col].mean()), 2),
                "negative_count": int((df[col] < 0).sum())
            }

        sample_records = df.head(3).to_dict(orient="records")

        return {
            "file": p.name,
            "total_rows": total_rows,
            "total_columns": total_cols,
            "columns": list(df.columns),
            "null_counts": null_counts,
            "duplicate_rows": duplicate_rows,
            "numeric_summary": numeric_summary,
            "sample_records": sample_records,
            "needs_cleaning": (duplicate_rows > 0 or any(v > 0 for v in null_counts.values()))
        }
    except Exception as e:
        return {"error": f"Failed to profile dataset: {str(e)}"}

@tool(name="clean_dataset", description="Automatically clean a CSV file (dedup, impute nulls, fix negative values, normalize text).")
def clean_dataset(file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """Applies standardized data hygiene transformations."""
    p = Path(file_path)
    if not p.is_absolute():
        p = config.BASE_DIR / p
    if not p.exists():
        return {"error": f"File '{file_path}' does not exist."}

    try:
        df = pd.read_csv(p) if p.suffix.lower() == ".csv" else pd.read_excel(p)
        initial_rows = len(df)

        # 1. Remove duplicate rows
        duplicates_removed = int(df.duplicated().sum())
        df = df.drop_duplicates()

        # 2. Trim string whitespace and normalize text
        for col in df.select_dtypes(include=["object", "string"]).columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "": None})

        # 3. Impute missing values
        imputed_counts = {}
        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                imputed_counts[col] = null_count
                if pd.api.types.is_numeric_dtype(df[col]):
                    median_val = df[col].median()
                    df[col] = df[col].fillna(median_val)
                else:
                    df[col] = df[col].fillna("Unknown")

        # 4. Handle negative values in typically positive fields (e.g. quantity, amount, price)
        outliers_adjusted = 0
        for col in df.select_dtypes(include=[np.number]).columns:
            col_lower = col.lower()
            if any(k in col_lower for k in ["qty", "quantity", "price", "amount", "cost", "units"]):
                neg_mask = df[col] < 0
                outliers_adjusted += int(neg_mask.sum())
                df.loc[neg_mask, col] = df.loc[neg_mask, col].abs()

        # 5. Format output
        out_p = Path(output_path) if output_path else config.CLEANED_DATA_DIR / f"cleaned_{p.name}"
        if not out_p.is_absolute():
            out_p = config.BASE_DIR / out_p
        out_p.parent.mkdir(parents=True, exist_ok=True)

        df.to_csv(out_p, index=False)

        return {
            "success": True,
            "original_file": str(p),
            "cleaned_file": str(out_p),
            "initial_rows": initial_rows,
            "final_rows": len(df),
            "duplicates_removed": duplicates_removed,
            "imputed_columns": imputed_counts,
            "outliers_adjusted": outliers_adjusted
        }
    except Exception as e:
        return {"error": f"Cleaning failed: {str(e)}", "success": False}

@tool(name="compute_summary_metrics", description="Compute aggregate business metrics and top groupings from tabular data.")
def compute_summary_metrics(file_path: str) -> Dict[str, Any]:
    """Generates executive summary metrics."""
    p = Path(file_path)
    if not p.is_absolute():
        p = config.BASE_DIR / p
    if not p.exists():
        return {"error": f"File '{file_path}' does not exist."}

    try:
        df = pd.read_csv(p)
        metrics = {
            "total_records": len(df)
        }
        
        # Calculate revenue/amount if present
        for col in df.columns:
            col_lower = col.lower()
            if any(k in col_lower for k in ["amount", "revenue", "total", "sales"]):
                metrics["total_value"] = round(float(df[col].sum()), 2)
                metrics["average_value"] = round(float(df[col].mean()), 2)
                break

        # Group by category if present
        for col in df.columns:
            if col.lower() in ["category", "region", "status", "type"]:
                metrics[f"by_{col.lower()}"] = df[col].value_counts().head(5).to_dict()
                break

        return metrics
    except Exception as e:
        return {"error": str(e)}
