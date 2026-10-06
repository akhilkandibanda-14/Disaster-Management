# Dataset Notes

Reserved for the provenance and preparation notes of the flood dataset supplied
for this project.

Record the following before training:

- source and license
- collection dates and geographic region
- column definitions and measurement units
- missing-value and invalid-record handling
- target definition and class balance
- train/test split strategy
- known limitations and leakage risks

## Model Coverage Policy

The INDOFLOODS model is **NOT** a nationwide continuous spatial prediction model. It is based on predefined gauge/catchment observations.

The current SafeMap AI implementation only permits predictions when the requested location is within the configured **50 km** reference-gauge coverage. 

**Note on Hyderabad Coverage:**
Hyderabad is currently outside model coverage. The nearest official gauge (INDOFLOODS-gauge-916) is ~71.77 km away, which exceeds the 50 km threshold. Therefore, SafeMap AI does not provide ML predictions for Hyderabad locations under the current model. 

Do **NOT** claim that SafeMap AI currently provides INDOFLOODS flood prediction for all of India.