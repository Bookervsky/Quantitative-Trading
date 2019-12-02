"""
The ``expected_returns`` module provides functions for estimating the expected returns of
the assets, which is a required input in mean-variance optimisation.

By convention, the output of these methods are expected *annual* returns. It is assumed that
*daily* prices are provided, though in reality the functions are agnostic
to the time period (just change the ``frequency`` parameter). Asset prices must be given as
a pandas dataframe, as per the format described in the :ref:`user-guide`.

All of the functions process the price data into percentage returns data, before
calculating their respective estimates of expected returns.

Currently implemented:
    - mean historical return
    - exponentially weighted mean historical return

Additionally, we provide utility functions to convert from returns to prices and vice-versa.
"""

import warnings
import numpy as np
import pandas as pd


def returns_from_prices(prices):
    """
    Calculate the returns given prices.

    :param prices: adjusted (daily) closing prices of the asset, each row is a
                   date and each column is a ticker/id.
    :type prices: pd.DataFrame
    :return: (daily) returns
    :rtype: pd.DataFrame
    """
    return prices.pct_change().dropna(how="all")


def prices_from_returns(returns):
    """
    Calculate the pseudo-prices given returns. These are not true prices because
    the initial prices are all set to 1, but it behaves as intended when passed
    to any PyPortfolioOpt method.

    :param returns: (daily) percentage returns of the assets
    :type returns: pd.DataFrame
    :return: (daily) pseudo-prices.
    :rtype: pd.DataFrame
    """
    ret = 1 + returns
    ret.iloc[0] = 1  # set first day pseudo-price
    return ret.cumprod()


def mean_historical_return(prices, frequency=252):
    """
    Calculate annualised mean (daily) historical return from input (daily) asset prices.

    :param prices: adjusted closing prices of the asset, each row is a date
                   and each column is a ticker/id.
    :type prices: pd.DataFrame
    :param frequency: number of time periods in a year, defaults to 252 (the number
                      of trading days in a year)
    :type frequency: int, optional
    :return: annualised mean (daily) return for each asset
    :rtype: pd.Series
    """
    if not isinstance(prices, pd.DataFrame):
        warnings.warn("prices are not in a dataframe", RuntimeWarning)
        prices = pd.DataFrame(prices)
    returns = returns_from_prices(prices)
    return returns.mean() * frequency


def ema_historical_return(prices, frequency=252, span=500):
    """
    Calculate the exponentially-weighted mean of (daily) historical returns, giving
    higher weight to more recent data.

    :param prices: adjusted closing prices of the asset, each row is a date
                   and each column is a ticker/id.
    :type prices: pd.DataFrame
    :param frequency: number of time periods in a year, defaults to 252 (the number
                      of trading days in a year)
    :type frequency: int, optional
    :param span: the time-span for the EMA, defaults to 500-day EMA.
    :type span: int, optional
    :return: annualised exponentially-weighted mean (daily) return of each asset
    :rtype: pd.Series
    """
    if not isinstance(prices, pd.DataFrame):
        warnings.warn("prices are not in a dataframe", RuntimeWarning)
        prices = pd.DataFrame(prices)
    returns = returns_from_prices(prices)
    return returns.ewm(span=span).mean().iloc[-1] * frequency


def black_litterman_return(Pi, Sigma, Q, Omega=None, P=None, tau=0.05):
    r"""
    Calculate the expected return according to the Black-Litterman model.

    This function receives a previous estimate of the implied equilibrum return for each asset.

    :param Pi: the implied equilibrum return for each asset
    :type Pi: pd.Series
    :param Sigma: the (symmetric) covariance matrix estimate
    :type Sigma: pd.DataFrame
    :param Q: the estimated return vector for every different view
    :type Q: pd.Series
    :param Omega: a (diagonal) matrix that identifies the uncertainty in the views (default is the diagonal of :math:`\tau P \Sigma P^T`)
    :type Omega: pd.DataFrame, optional
    :param P: the matrix that identifies the asset involved in the different views (default is identity)
    :type P: pd.DataFrame, optional
    :param tau: the weight-on-views scalar (default is 0.05)
    :type tau: float, optional
    :return: the new combined return for each asset
    :rtype: pd.Series
    """
    if P is None:
        P = np.eye(Sigma.shape[0])
    if Omega is None:
        Omega = np.diag(np.diag(tau * P @ Sigma @ P.T))

    Omega_inv = np.diag(1.0 / np.diag(Omega))
    P_Omega_inv = P.T @ Omega_inv
    tau_Sigma_inv = np.linalg.inv(tau * Sigma)

    A = tau_Sigma_inv + P_Omega_inv @ P
    b = tau_Sigma_inv.dot(Pi) + P_Omega_inv.dot(Q)
    x = np.linalg.solve(A, b)
    return pd.Series(x, index=Pi.index)
