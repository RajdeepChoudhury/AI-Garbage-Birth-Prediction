# Models and forecasts

## Data

Each row is one ward on one day. The generator in `ml/data/generate_synthetic.py` simulates garbage backlog that grows daily and drops after each scheduled pickup. Rain, heat, festivals, holidays, construction, markets, restaurants, traffic and population all push volume up. Targets are tomorrow's volume, a four level risk label and a hotspot probability.

Because the pickup schedule dominates this process, schedule related features (day of week, pickup gap, collection frequency) rank highest in SHAP. That reflects how the data was built, not a finding about any real city.

## Evaluation method

Models are trained on the earlier 80 percent of dates and tested on the most recent 20 percent, so scores measure forecasting forward in time. Classification scores are macro averaged across the four risk levels. The last column is F1 for the combined High and Critical group, which is the group that matters most operationally.

## Results on the synthetic data

Volume forecast (regression):

| Model | MAE | RMSE | R2 |
|---|---|---|---|
| Random Forest | 0.226 | 0.312 | 0.970 |
| XGBoost | 0.222 | 0.306 | 0.971 |
| LightGBM | 0.224 | 0.308 | 0.971 |
| CatBoost (best) | 0.223 | 0.306 | 0.971 |

Risk level (classification):

| Model | Precision | Recall | F1 | F1 High and Critical |
|---|---|---|---|---|
| Random Forest (best) | 0.828 | 0.859 | 0.842 | 0.943 |
| XGBoost | 0.838 | 0.845 | 0.841 | 0.941 |
| LightGBM | 0.831 | 0.849 | 0.839 | 0.943 |
| CatBoost | 0.812 | 0.859 | 0.833 | 0.944 |

The four models are close, which is expected for rule driven synthetic data. Treat the ranking as unreliable until real data is used.

## Not yet evaluated

LSTM, Temporal Fusion Transformer and Graph Neural Network were requested but not built. They need PyTorch and much longer training, and a sequence model needs enough real history per ward to be worth it.

## How each forecast field is produced

| Field | How |
|---|---|
| predicted_volume | Best regressor output for the next day, never below zero |
| risk_level | Best classifier, class with the highest probability |
| confidence | Probability of that predicted class |
| hotspot_probability | Classifier probability of High plus Critical |
| urgency_score | 0 to 100. Half hotspot probability, half predicted volume relative to 1.5 times overflow capacity |
| recommended_cleaning_time | Urgency 75 or more: within 6 hours. 50 or more: within 24 hours. 25 or more: within 48 hours. Otherwise next scheduled collection |
| predicted_overflow_date | Forecast date if volume already exceeds capacity. Otherwise a straight line projection from the predicted daily change, or none if no overflow is expected within 7 days |
| top_factors | SHAP values of the regressor, top five by size, in volume units |

## Retraining

Run `python train.py` in `ml`. It overwrites the files in `ml/artifacts`. Restart the backend afterwards so it loads the new models.

## Moving to real data

Replace the generator with a loader that produces the same columns. Then recalibrate `OVERFLOW_CAPACITY` per ward, check the risk thresholds, and review whether the heuristics above match how your teams actually decide.
