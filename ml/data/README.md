# Flood Dataset Upload Area

Place the approved flood dataset in this directory when it is available.

Expected minimum CSV fields:

- `latitude`
- `longitude`
- `rainfall`
- `temperature`
- `humidity`
- `water_level`
- `elevation`
- `flood_occurrence` or `flood_risk` as the target

Do not upload API keys, personal data, or a dataset that cannot be legally used
for this project. Keep the original source, license, collection period, units,
and preprocessing notes in `docs/dataset-notes.md` when the dataset arrives.

The repository does not include synthetic training data. Demo records shown by
the application must never be used as evidence of model accuracy.