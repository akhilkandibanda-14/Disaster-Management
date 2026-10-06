from datetime import date
import pandas as pd
from app.services.integration import IntegrationService

# Initialize the service
svc = IntegrationService(data_dir="../data/raw/indofloods")

# Target date
target_date = date(2023, 8, 1)

# Hyderabad coords (from user prompt)
lat = 17.385
lon = 78.486

# Get the vector
vector = svc.build_feature_vector(lat, lon, target_date, max_dist_km=2000.0) # set max dist large so it finds the closest gauge

# Create dataframe
df = pd.DataFrame([vector])[svc.num_cols + svc.cat_cols]

# Pass through preprocessor
processed = svc.pipeline.named_steps['preprocessor'].transform(df)

print(f"Raw shape: {df.shape}")
print(f"Transformed shape: {processed.shape}")

rf = svc.pipeline.named_steps['model']
print(f"Final model input shape expected: {rf.n_features_in_}")
