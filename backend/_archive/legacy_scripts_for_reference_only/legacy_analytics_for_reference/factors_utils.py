'''calculating factor betas'''
import logging

import numpy
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.formula.api import ols

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def calculate_position_betas(
    factor_returns: pd.DataFrame,
    position_returns: pd.DataFrame,
) -> pd.DataFrame:
    '''
    Calculates the adjusted position-level betas for each factor.

    Args:
        factor_returns (pd.DataFrame): A DataFrame of factor returns
            long format.
        position_returns (pd.DataFrame): A DataFrame of position returns per day
            long format.

    Returns:
        pd.DataFrame: A DataFrame of adjusted position-level betas for
            each factor, with position names as index and factor names as columns.
    '''

    # Position level beta to each factor
    factor_returns_long = factor_returns\
        .reset_index()\
        .melt(
            id_vars='date',
            var_name='factor',
            value_name='factor_return',
        )
    # print(factor_returns_long)

    position_returns_long = position_returns\
        .reset_index()\
        .rename(
            columns={
                'return': 'position_return',
                'TradeDate': 'date',
                'VaRTicker': 'position'
            }
        )\
        .melt(
            id_vars='date',
            var_name='position',
            value_name='position_return',
        )

    # Merge factor and position returns
    merged_returns = pd.merge(
        factor_returns_long, position_returns_long, on='date', how='inner')

    # Calculate factor-adjusted returns for each position
    merged_returns['factor_rf'] = merged_returns['factor_return'] \
        - merged_returns.groupby('factor')['factor_return'].transform('mean')
    merged_returns['position_rf'] = merged_returns['position_return'] \
        - merged_returns.groupby('position')['factor_return'].transform('mean')

    # Calculate beta factors for each position and factor
    numerator = calculate_beta_factor_numerator(merged_returns)
    denominator = calculate_beta_factors_denominator(merged_returns)
    beta_factors = numerator / denominator

    # Reshape beta factors into a DataFrame
    beta_factors_df = beta_factors\
        .unstack(level=1)\
        .droplevel(1)\
        .T

    beta_factors_df.index.name = 'ID'
    beta_factors_df.reset_index(inplace=True)

    return beta_factors_df


def calculate_beta_factor_numerator(merged_returns):
    '''calculates the numerator to calculate factor betas'''

    return merged_returns\
        .groupby(['factor', 'position'])[['position_rf', 'factor_rf']]\
        .cov()\
        .iloc[::2, 1]


def calculate_beta_factors_denominator(merged_returns):
    '''calculates the denominator to calculate factor betas'''
    return merged_returns.groupby('factor')['factor_rf'].var()
