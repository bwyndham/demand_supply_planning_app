# Demand and Supply Planning App

Welcome to the Demand and Supply Planning App, an educational project by Ben Wyndham.

The purpose of this app is to provide automatic, high-quality, hierarchical demand forecasting and supply planning via a simple interface. This app is purely educational, and assumptions or notes are listed throughout the app.

The forecasts are driven by an ML and Statistical forecaster that selects the best model for each time series, based on crossvalidation performance across 10, 6 week folds. This forecaster uses a wide selection of models such as LightGBM, Croston, HoltWinters, and ETS. The code for the forecaster can be found in this github repo.

This app uses the Nixtla, LightGBM, Streamlit, Pandas, Gspread and Plotly Python libraries.
