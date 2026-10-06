# Flood Risk ML Model Quality Report

## 1. Dataset Overview
- **Dataset Size**: 10,000 samples, 14 features.
- **Features Analyzed**: Latitude, Longitude, Rainfall (mm), Temperature (°C), Humidity (%), River Discharge (m³/s), Water Level (m), Elevation (m), Population Density, Infrastructure, Historical Floods, Land Cover, Soil Type.
- **Target Variable**: `Flood Occurred` (Binary: 0 or 1).

## 2. Target Distribution
The target variable is almost perfectly balanced:
- **Flood Occurred = 1**: 50.57% (5,057 samples)
- **Flood Occurred = 0**: 49.43% (4,943 samples)

## 3. Feature Analysis
The distributions of the input features are nearly identical regardless of whether a flood occurred or not.
- **Numerical Features**: The mean and standard deviation of critical features (like Rainfall, Water Level, and River Discharge) show no significant difference between the two classes.
  - *Rainfall (mm) Mean*: 150.20 (Flood=0) vs 149.83 (Flood=1)
  - *Water Level (m) Mean*: 5.03 (Flood=0) vs 5.00 (Flood=1)
  - *River Discharge (m³/s) Mean*: 2518.8 (Flood=0) vs 2512.7 (Flood=1)
- **Categorical Features**: The target rates for all categories (e.g., across all Soil Types and Land Covers) are approximately ~50%, matching the overall target distribution.

## 4. Evidence of Predictive Signal
There is **no evidence of a meaningful predictive signal**. 
A Pearson correlation analysis between the numerical features and the target variable reveals that all correlations are virtually zero.
- `Humidity (%)`: 0.027
- `Temperature (°C)`: -0.015
- `Historical Floods`: 0.012
- `Water Level (m)`: -0.005
- `Rainfall (mm)`: -0.002

In a real-world scenario, features like Rainfall, Water Level, and River Discharge would exhibit a strong positive correlation with flood occurrence.

## 5. Possible Synthetic/Random Target Evidence
The dataset exhibits strong characteristics of being **synthetically generated with a random target variable**:
1. **Unrealistic Relationships**: Critical environmental predictors (Rainfall, Water Level) have zero correlation with the flood target.
2. **Identical Distributions**: The feature distributions for the positive class and negative class are statistically indistinguishable.
3. **Model Performance Ceiling**: No machine learning model is able to find a pattern, defaulting to random guessing (~50% accuracy).

## 6. Baseline Model Comparison
Various baseline models were trained on the same 80% training set and evaluated on the untouched 20% test set:
- **DummyClassifier (Majority Class)**: Accuracy 50.55%, F1 67.15%
- **LogisticRegression**: Accuracy 49.65%, F1 50.36%
- **RandomForestClassifier**: Accuracy 49.50%, F1 49.50%
- **ExtraTreesClassifier**: Accuracy 50.75%, F1 51.21%
- **HistGradientBoosting**: Accuracy 52.00%, F1 52.66%

None of the machine learning models significantly outperform the dummy classifier, confirming the lack of extractable signal.

## 7. Cross-Validation Results
A 5-fold Stratified K-Fold cross-validation using the Random Forest model on the training data yielded:
- **Mean Accuracy**: 51.61% ± 0.99%
- **Mean Precision**: 52.19% ± 0.99%
- **Mean Recall**: 51.63% ± 1.03%
- **Mean F1**: 51.91% ± 0.89%

## 8. Final Test Results (Current Model)
- **Accuracy**: 51.45%
- **Precision**: 51.97%
- **Recall**: 52.13%
- **F1 Score**: 52.05%

## 9. Feature Importance
Because the target is random, feature importances derived from the Random Forest model are uniformly distributed across all features (around 0.09 - 0.10 for each numeric feature). The model is essentially picking noise equally from all variables rather than splitting on strong predictors.

## 10. Data Leakage Assessment
No data leakage was found. The target variable is strictly separated from the features during training and preprocessing. The low performance further confirms that no accidental target leakage exists.

## 11. Final Model Decision
**OPTION B**: The dataset does not contain enough predictive signal. 

I did not force an improvement or fabricate a high accuracy. The dataset is not currently suitable for reliable flood prediction because the target variable is entirely disconnected from the input features. The original Step 1 model will be kept as the best valid representation of this dataset.

## 12. Recommendation
To build a functional Flood Risk ML Model, a new, genuine historical dataset is required. The dataset must contain real-world correlations where high rainfall, high river discharge, and high water levels logically correspond to flood events.
