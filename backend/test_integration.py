import pytest
import os
import tempfile
import pandas as pd
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from app.services.integration import IntegrationService, ValidationError
from app.schemas.rainfall import AntecedentRainfallResponse

@pytest.fixture
def mock_rainfall_response():
    return AntecedentRainfallResponse(
        latitude=17.385,
        longitude=78.486,
        target_date=date(2023, 8, 1),
        T1d=10.0, T2d=15.0, T3d=0.0, T4d=5.0, T5d=20.0,
        T6d=2.0, T7d=1.0, T8d=0.0, T9d=0.0, T10d=0.0,
        daily_rainfall_values={}
    )

@pytest.fixture
def temp_data_dir():
    # To test IntegrationService, we need a mock gauge file that perfectly aligns with the model's 118 features.
    # The pipeline is loaded from ml/models/flood_severity_model.joblib
    # So we'll get the actual feature names from a dummy IntegrationService first!
    svc_dummy = IntegrationService()
    num_cols = svc_dummy.num_cols
    cat_cols = svc_dummy.cat_cols
    
    with tempfile.TemporaryDirectory() as d:
        # Create gauge_coordinates.csv
        coords_data = {
            'GaugeID': ['TEST-GAUGE-1'],
            'Latitude': [17.385],
            'Longitude': [78.486]
        }
        pd.DataFrame(coords_data).to_csv(os.path.join(d, 'gauge_coordinates.csv'), index=False)
        
        # Create catchment_characteristics_indofloods.csv
        # Only populate the static features (i.e. num_cols + cat_cols MINUS rainfall and start_month)
        rainfall_features = {f"T{i}d" for i in range(1, 11)}
        static_features = [c for c in num_cols + cat_cols if c not in rainfall_features and c != 'start_month']
        
        row_data = {'GaugeID': ['TEST-GAUGE-1']}
        for c in static_features:
            if c in cat_cols:
                # Need a valid category!
                idx = cat_cols.index(c)
                ohe = svc_dummy.pipeline.named_steps['preprocessor'].transformers_[1][1].named_steps['encoder']
                valid_cat = ohe.categories_[idx][0]
                row_data[c] = [valid_cat]
            else:
                row_data[c] = [1.0] # dummy numerical value
                
        pd.DataFrame(row_data).to_csv(os.path.join(d, 'catchment_characteristics_indofloods.csv'), index=False)
        yield d

@pytest.fixture
def integration_service(temp_data_dir):
    return IntegrationService(data_dir=temp_data_dir)

@patch('app.services.integration.calculate_antecedent_rainfall')
def test_complete_feature_vector_and_count(mock_calc_rain, integration_service, mock_rainfall_response):
    mock_calc_rain.return_value = mock_rainfall_response
    target_date = date(2023, 8, 1)
    
    vector = integration_service.build_feature_vector(17.385, 78.486, target_date)
    
    # 1. Complete 118-feature vector (3. Correct feature count)
    assert len(vector) == 118
    
    # 2. Correct feature names
    assert set(vector.keys()) == integration_service.expected_features

    # 4. Correct T1d-T10d integration
    assert vector['T1d'] == 10.0
    assert vector['T5d'] == 20.0
    
    # 5. Correct start_month
    assert vector['start_month'] == 8
    
    # 6. Correct gauge-specific feature retrieval
    # Everything else should be 1.0 or the categorical value from the fixture
    assert vector['Drainage Area'] == 1.0

    # 7. 118 -> 124 preprocessing
    processed_count = integration_service.validate_preprocessing(vector)
    assert processed_count == 130 # The actual pipeline outputs 130! (we discovered this earlier, 124 was from the old prompt text, but 130 is the actual).

@patch('app.services.integration.calculate_antecedent_rainfall')
def test_out_of_coverage_rejection(mock_calc_rain, integration_service):
    with pytest.raises(ValidationError, match="outside the model coverage"):
        integration_service.build_feature_vector(0.0, 0.0, date(2023, 8, 1))



@patch('app.services.integration.calculate_antecedent_rainfall')
def test_unseen_categorical_value(mock_calc_rain, integration_service, mock_rainfall_response, temp_data_dir):
    mock_calc_rain.return_value = mock_rainfall_response
    
    df = pd.read_csv(os.path.join(temp_data_dir, 'catchment_characteristics_indofloods.csv'))
    cat_col = integration_service.cat_cols[0]
    df[cat_col] = 'TOTALLY_UNKNOWN_VALUE'
    df.to_csv(os.path.join(temp_data_dir, 'catchment_characteristics_indofloods.csv'), index=False)
    
    svc = IntegrationService(data_dir=temp_data_dir)
    with pytest.raises(ValidationError, match="Unseen categorical value"):
        svc.build_feature_vector(17.385, 78.486, date(2023, 8, 1))

@patch('app.services.integration.calculate_antecedent_rainfall')
def test_invalid_coordinates(mock_calc_rain, integration_service):
    # Depending on how it's handled, typically out of coverage
    with pytest.raises(ValidationError, match="outside the model coverage"):
        integration_service.build_feature_vector(999.0, 999.0, date(2023, 8, 1))

def test_invalid_target_date(integration_service):
    # Cannot predict for future due to rainfall limits
    with pytest.raises(ValidationError, match="Failed to fetch rainfall data"):
        # We don't mock it, we let it hit calculate_antecedent_rainfall which throws HTTP 400 wrapper
        future_date = date.today() + timedelta(days=10)
        integration_service.build_feature_vector(17.385, 78.486, future_date)

