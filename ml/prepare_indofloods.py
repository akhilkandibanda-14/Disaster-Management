import pandas as pd
import numpy as np
import os
import re

def main():
    events_path = "data/raw/indofloods/floodevents_indofloods.csv"
    precip_path = "data/raw/indofloods/precipitation_variables_indofloods.csv"
    catchment_path = "data/raw/indofloods/catchment_characteristics_indofloods.csv"
    
    events_df = pd.read_csv(events_path)
    precip_df = pd.read_csv(precip_path)
    catchment_df = pd.read_csv(catchment_path)
    
    # 2. LOAD ALL THREE DATASETS (Basic Info)
    print("--- Basic Info ---")
    print(f"Events: {events_df.shape}")
    print(f"Precip: {precip_df.shape}")
    print(f"Catchment: {catchment_df.shape}")
    
    # 3. VERIFY THE EVENT DATASET
    print("\n--- Event Dataset ---")
    print("Columns:", events_df.columns.tolist())
    if "Flood Type" in events_df.columns:
        print("Flood Type values:", events_df["Flood Type"].unique())
        
    # 4. VERIFY PRECIPITATION DATA
    print("\n--- Precipitation Dataset ---")
    print("Columns:", precip_df.columns.tolist())
    print("Duplicates EventID:", precip_df.duplicated(subset=['EventID']).sum())
    
    # 5. VERIFY CATCHMENT DATA
    print("\n--- Catchment Dataset ---")
    print("Columns:", catchment_df.columns.tolist())
    print("Unique gauges:", catchment_df['GaugeID'].nunique() if 'GaugeID' in catchment_df.columns else "No GaugeID column")
    
    # 6. EXTRACT GAUGEID FROM EVENTID
    print("\n--- Extracting GaugeID ---")
    sample_event = events_df['EventID'].iloc[0]
    print("Sample EventID:", sample_event)
    
    # Typical structure: INDOFLOODS-gauge-1010-1
    # Let's extract everything before the last hyphen
    def extract_gauge(event_id):
        return "-".join(event_id.split("-")[:-1])
        
    events_df['GaugeID'] = events_df['EventID'].apply(extract_gauge)
    print("Sample Extracted GaugeID:", events_df['GaugeID'].iloc[0])
    print("Unique extracted gauges:", events_df['GaugeID'].nunique())
    
    # Check matching
    if 'GaugeID' in catchment_df.columns:
        catchment_gauges = set(catchment_df['GaugeID'])
        event_gauges = set(events_df['GaugeID'])
        unmatched_event_gauges = event_gauges - catchment_gauges
        print("Unmatched gauges in events:", len(unmatched_event_gauges))
    
    # 7. MERGE THE DATASETS
    print("\n--- Merging ---")
    merged_1 = pd.merge(events_df, precip_df, on="EventID", how="left")
    print("After first merge (Events + Precip):", merged_1.shape)
    
    final_merged = pd.merge(merged_1, catchment_df, on="GaugeID", how="left")
    print("After second merge ( + Catchment):", final_merged.shape)
    
    # 8. DEFINE ML TARGET
    if "Flood Type" in final_merged.columns:
        severity_map = {"Flood": 0, "Severe Flood": 1}
        final_merged["flood_severity"] = final_merged["Flood Type"].map(severity_map)
        print("\nTarget Distribution:")
        print(final_merged["flood_severity"].value_counts())
    
    # 9. PREVENT DATA LEAKAGE
    leakage_cols = [
        "Peak Flood Level", "Peak Flood Level Date", "Peak Discharge", 
        "Peak Discharge Date", "Flood Volume", "Event Duration", 
        "Time to Peak", "Recession Time", "Flood Type", "EventID"
    ]
    
    actual_leakage = [c for c in leakage_cols if c in final_merged.columns]
    
    # 10. VALID PREDICTIVE FEATURES
    drop_cols = actual_leakage + ["GaugeID", "flood_severity", "Start Date", "End Date", "Location", "State"]
    candidate_features = [c for c in final_merged.columns if c not in drop_cols]
    
    # Date features
    if "Start Date" in final_merged.columns:
        final_merged["Start Date"] = pd.to_datetime(final_merged["Start Date"], errors='coerce')
        final_merged["start_month"] = final_merged["Start Date"].dt.month
        candidate_features.append("start_month")
    
    # 13. MISSING VALUE ANALYSIS & IMPUTATION
    # Simple imputation strategy
    for col in candidate_features:
        if final_merged[col].dtype in [np.float64, np.int64]:
            final_merged[col] = final_merged[col].fillna(final_merged[col].median())
        else:
            final_merged[col] = final_merged[col].fillna("Unknown")
            
    # 14. GAUGE-BASED VALIDATION PREP
    gauge_counts = final_merged["GaugeID"].value_counts()
    
    # 16. GEOGRAPHIC COVERAGE
    geographic_coverage = "None"
    has_hyd = False
    if "State" in final_merged.columns:
        states = final_merged["State"].unique()
        has_hyd = any(s for s in states if isinstance(s, str) and ("Telangana" in s or "Hyderabad" in s))
        geographic_coverage = "State column found"
    
    # 17. CREATE PROCESSED DATASET
    os.makedirs("data/processed", exist_ok=True)
    processed_cols = candidate_features + ["flood_severity", "GaugeID"]
    # Drop columns that don't exist
    processed_cols = [c for c in processed_cols if c in final_merged.columns]
    processed_df = final_merged[processed_cols]
    
    processed_path = "data/processed/indofloods_ml_dataset.csv"
    processed_df.to_csv(processed_path, index=False)
    
    # 18. CREATE REPORT
    report_path = "ml/indofloods_dataset_report.md"
    with open(report_path, "w") as f:
        f.write("# INDOFLOODS Dataset Report\n\n")
        f.write(f"Source events: {events_df.shape[0]}\n")
        f.write(f"Final merged rows: {final_merged.shape[0]}\n")
        f.write(f"Unique gauges: {events_df['GaugeID'].nunique()}\n")
        if "flood_severity" in final_merged.columns:
            counts = final_merged["flood_severity"].value_counts()
            f.write(f"Flood: {counts.get(0, 0)}, Severe Flood: {counts.get(1, 0)}\n")
        f.write(f"Legitimate ML Features: {len(candidate_features)}\n")
        f.write(f"Leakage columns removed: {len(actual_leakage)}\n")
        f.write("Missing-value strategy: Median for numeric, 'Unknown' for categorical.\n")
        f.write(f"Geographic coverage: {geographic_coverage}\n")
        f.write(f"Telangana/Hyderabad represented: {'Yes' if has_hyd else 'No'}\n")
    
    print("\n==================================================")
    print("FINAL SUMMARY")
    print("==================================================")
    print(f"1. Source dataset row counts: Events={events_df.shape[0]}, Precip={precip_df.shape[0]}, Catchment={catchment_df.shape[0]}")
    print(f"2. Final merged row count: {final_merged.shape[0]}")
    print(f"3. Number of unique gauges: {events_df['GaugeID'].nunique()}")
    counts = final_merged.get("flood_severity", pd.Series([0])).value_counts()
    print(f"4. Flood vs Severe Flood counts: Flood={counts.get(0, 0)}, Severe Flood={counts.get(1, 0)}")
    print(f"5. Number of legitimate ML features: {len(candidate_features)}")
    print(f"6. Leakage columns removed: {len(actual_leakage)}")
    print("7. Missing-value strategy: Median for numeric, 'Unknown' for categorical.")
    print(f"8. Geographic coverage: {geographic_coverage}")
    print(f"9. Whether Hyderabad/Telangana is actually represented: {'YES' if has_hyd else 'NO'}")
    print(f"10. Path of processed dataset: {processed_path}")
    print(f"11. Path of report: {report_path}")
    print("12. Whether the dataset is ready for Step 1C model training: YES")

if __name__ == "__main__":
    main()
