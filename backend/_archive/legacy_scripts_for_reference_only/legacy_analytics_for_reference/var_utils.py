import numpy as np
import pandas as pd



def multiply_matrices(
    matrix_cov: pd.DataFrame,
    exposure: pd.DataFrame,
    factor_betas: pd.DataFrame
) -> pd.DataFrame:
    '''
    matrix multiplication to calculate VaR

    Args:
        matrix_cov: pd.DataFrame
        exposure: pd.DataFrame
        factor_betas_fund: pd.DataFrame
    '''
    exposure_t = exposure.T
    factor_betas_t = factor_betas.T

    position_exposure = exposure_t\
        .dot(factor_betas)\
        .dot(matrix_cov)\
        .dot(factor_betas_t)\
        .T
    return (position_exposure ** .5)


def correlation_matrix(
    factor_returns: pd.DataFrame,
    factor: pd.DataFrame,
) -> pd.DataFrame:
    '''calculates factor correlation matrix'''

    factor_correl = factor_returns.corr()
    factor.set_index(["FactorID"], inplace=True)
    factor_correl = pd.merge(
        factor_correl, factor["Factor Names"],
        left_index=True,
        right_index=True,
    )
    factor_correl.reset_index(inplace=True, drop=True)
    factor_correl.set_index(["Factor Names"], inplace=True)

    return factor_correl


def decay_covariance_matrix(factor_returns: pd.DataFrame) -> pd.DataFrame:
    '''calculates covariance matrix with decay function'''

    intervals = np.linspace(start=1, stop=len(
        factor_returns), num=len(factor_returns))
    data = ((1 - 0.94) * 0.94 ** (intervals - 1)) ** (0.5)  # type: ignore
    df_tmp = np.repeat(data, len(factor_returns.columns))
    df_tmp = df_tmp.reshape(len(data), len(factor_returns.columns))
    factor_returns_decay = factor_returns * df_tmp
    factor_covar_decay = factor_returns_decay.cov()

    return factor_covar_decay


def covariance_matrix(factor_returns: pd.DataFrame) -> pd.DataFrame:
    '''calculates covariance matrix betweem factor returns'''

    factor_cov = factor_returns.cov()
    return factor_cov
