# INDOFLOODS Flood Severity Model Report

**IMPORTANT: This model is trained on INDOFLOODS data and does not represent Hyderabad/Telangana-specific flood behavior.**

## 1. Dataset Information
- Dataset: data/processed/indofloods_ml_dataset.csv
- Training Rows: 3760
- Testing Rows: 788

## 2. Methodology
- Grouping Methodology: GroupShuffleSplit and GroupKFold using `GaugeID` to prevent data leakage across events at the same gauge.
- Gauge Overlap between Train/Test: 0

## 3. Best Model Performance
- Best Model: RandomForest
- Test Accuracy: 0.6739
- Test Precision: 0.5450
- Test Recall: 0.4368
- Test F1: 0.4850
- Test ROC-AUC: 0.6682
- Grouped CV F1 Mean: 0.3405 ± 0.1377

## 4. Confusion Matrix
```
[[410 101]
 [156 121]]
```

## 5. Overfitting Analysis
- Training F1: 0.9982
- Test F1: 0.4850
- Analysis: Significant overfitting observed. The model memorized training gauges but generalized poorly to new gauges.

## 6. Deployment Suitability
While the model can be used to complete Step 2 pipeline integration, its real-world accuracy heavily depends on whether the INDOFLOODS data translates well to the specific local use case. Since this does not cover Telangana, it is technically a placeholder for the actual API structure.
