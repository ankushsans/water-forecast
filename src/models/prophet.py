from fbprophet import Prophet
from dill import dump
import pandas as pd
import os
from src.models.model import ModelStrategy

class ProphetModel(ModelStrategy):
    '''
    A class representing a Prophet model and standard operations on it
    '''

    def __init__(self, hparams, log_dir=None):
        univariate = True
        name = 'Prophet'
        self.changepoint_prior_scale = hparams.get('CHANGEPOINT_PRIOR_SCALE', 0.05)
        self.seasonality_prior_scale = hparams.get('SEASONALITY_PRIOR_SCALE', 10)
        self.holidays_prior_scale = hparams.get('HOLIDAYS_PRIOR_SCALE', 10)
        self.seasonality_mode = hparams.get('SEASONALITY_MODE', 'additive')
        self.changepoint_range = hparams.get('CHANGEPOINT_RANGE', 0.8)

        # Build DataFrame of local holidays
        holiday_dfs = []
        for holiday in hparams.get('HOLIDAYS', []):
            holiday_dfs.append(pd.DataFrame({
                'holiday': holiday,
                'ds': pd.to_datetime(hparams['HOLIDAYS'][holiday]),
                'lower_window': 0,
                'upper_window': 1}))
        self.local_holidays = pd.concat(holiday_dfs)

        model = Prophet(yearly_seasonality=True, holidays=self.local_holidays, changepoint_prior_scale=self.changepoint_prior_scale,
                        seasonality_prior_scale=self.seasonality_prior_scale, holidays_prior_scale=self.holidays_prior_scale,
                        seasonality_mode=self.seasonality_mode, changepoint_range=self.changepoint_range)
        model.add_country_holidays(country_name=hparams['COUNTRY'])   # Add country-wide holidays
        super(ProphetModel, self).__init__(model, univariate, name, log_dir=log_dir)


    def fit(self, dataset):
        '''
        Fits a Prophet forecasting model
        :param dataset: A Pandas DataFrame with 2 columns: Date and Consumption
        '''
        if dataset.shape[1] != 2:
            raise Exception('Univariate models cannot fit with datasets with more than 1 feature.')
        dataset.rename(columns={'Date': 'ds', 'Consumption': 'y'}, inplace=True)
        self.model.fit(dataset)
        return


    def evaluate(self, train_set, test_set, save_dir=None):
        '''
        Evaluates performance of Prophet model on test set
        :param train_set: A Pandas DataFrame with 2 columns: Date and Consumption
        :param test_set: A Pandas DataFrame with 2 columns: Date and Consumption
        '''
        train_set.rename(columns={'Date': 'ds', 'Consumption': 'y'}, inplace=True)
        test_set.rename(columns={'Date': 'ds', 'Consumption': 'y'}, inplace=True)
        df_prophet = self.model.make_future_dataframe(periods=test_set.shape[0], include_history=True, freq='D')
        df_prophet = self.model.predict(df_prophet)
        df_train = train_set.merge(df_prophet[["ds", "yhat"]],
                                    how="left").rename(columns={'yhat': 'model', 'y': 'gt'}).set_index("ds")
        df_test = test_set.merge(df_prophet[["ds", "yhat"]],
                                  how="left").rename(columns={'yhat': 'forecast', 'y': 'gt'}).set_index("ds")
        df_forecast = df_train.append(df_test)
        test_metrics = self.evaluate_forecast(df_forecast, save_dir=save_dir)
        return test_metrics


    def forecast(self, days, recent_data=None):
        future_dates = self.model.make_future_dataframe(periods=days)
        return self.model.predict(future_dates)


    def save_model(self, save_dir):
        '''
        Saves the model to disk
        :param save_dir: Directory in which to save the model
        '''
        if self.model:
            model_path = os.path.join(save_dir, self.name + self.train_date + '.pkl')
            dump(self.model, open(model_path, 'wb'))  # Serialize and save the model object



