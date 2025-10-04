import json
import logging
from argparse import ArgumentParser
from typing import Dict, List, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import statsmodels.api as sm
from pandas_market_calendars import get_calendar

from database_dockyard_capital_mgmt import AWSClient

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Disable scientific notation
pd.set_option("display.float_format", lambda x: "%.2f" % x)

style_factors_list = pd.read_csv("data/style_factors_meta.csv")


def pull_portfolio_holdings(
    aws_client: AWSClient,
    multi_portfolio_list: Union[None, List],
    fund: Union[None, str],
) -> pd.DataFrame:
    if multi_portfolio_list is None:
        query = f"""
                SELECT
                t1. *, 
                t2.symbol as t2_symbol, 
                t2."gics sector" as t2_gics_sector, 
                t2."gics industry" as t2_gics_industry, 
                t2.date as t2_date, 
                t2.run_date as t2_run_date
                FROM "fund_holdings"."portfolio_holdings"
                AS t1 LEFT JOIN "gics"."gics_classification"
                AS t2 ON t1.symbol = t2.symbol
                AND t2.run_date <= t1.date
                where fund in ('{fund}')
                ORDER by t1.date
                """
    else:
        query = f"""
                SELECT
                t1. *, 
                t2.symbol as t2_symbol, 
                t2."gics sector" as t2_gics_sector, 
                t2."gics industry" as t2_gics_industry, 
                t2.date as t2_date, 
                t2.run_date as t2_run_date
                FROM "fund_holdings"."portfolio_holdings"
                AS t1 LEFT JOIN "gics"."gics_classification"
                AS t2 ON t1.symbol = t2.symbol
                AND t2.run_date <= t1.date
                where fund in '{multi_portfolio_list}'
                ORDER by t1.date
                """
    data = aws_client.query_athena(query)

    return data


def pull_market_prices(
    aws_client: AWSClient, min_date: str, max_date: str, tickers: list
) -> pd.DataFrame:
    query = f"""
        SELECT *
        FROM market_prices.polygon_data
        WHERE id IN ({','.join([f"'{ticker}'" for ticker in tickers])})
        AND date >= '{min_date}' AND date <= '{max_date}'
    """
    data = aws_client.query_athena(query)

    return data


def copy_dataframe(df: pd.DataFrame, meta_index: pd.DatetimeIndex) -> pd.DataFrame:
    # Create an empty list to store the copied dataframes
    copied_dfs = []

    # Iterate over each date in the meta_index
    for date in meta_index:
        # Copy the original dataframe
        copied_df = df.copy()
        # Set the date as the new datetime index
        copied_df.set_index(pd.to_datetime([date] * len(df)), inplace=True)
        # Append the copied dataframe to the list
        copied_dfs.append(copied_df)
    # Concatenate all the copied dataframes into a single dataframe
    holdings_df = pd.concat(copied_dfs)
    holdings_df = holdings_df.rename_axis("date")

    return holdings_df


def agg_exposure_by_period(holdings_df: pd.DataFrame):
    dict = {}
    long_exposure_by_period = (
        holdings_df.groupby("holdings date")["exposure"]
        .agg(lambda x: x[x > 0].sum())
        .rename("long_exposure")
    )
    short_exposure_by_period = (
        holdings_df.groupby("holdings date")["exposure"]
        .agg(lambda x: x[x < 0].abs().sum())
        .rename("short_exposure")
    )
    # Group by date and calculate net exposure
    net_exposure_by_period = (
        holdings_df.groupby("holdings date")["exposure"].sum().rename("net_exposure")
    )
    # Calculate gross exposure using absolute values
    gross_exposure_by_period = (
        holdings_df.groupby("holdings date")["exposure"]
        .agg(lambda x: abs(x).sum())
        .rename("gross_exposure")
    )
    # Calculate gross exposure using absolute values
    mkt_value_by_period = (
        holdings_df.groupby("holdings date")["mkt val"]
        .agg(lambda x: x.sum())
        .rename("market_value")
    )
    # concat aggregated $ exposures and $ market values into a new DataFrame
    dict["holdings_df_by_period_dollar_agg"] = pd.concat(
        [
            long_exposure_by_period,
            short_exposure_by_period,
            net_exposure_by_period,
            gross_exposure_by_period,
            mkt_value_by_period,
        ],
        axis=1,
    )
    # imply % exposures
    dict["holdings_df_by_period_pct_agg"] = dict[
        "holdings_df_by_period_dollar_agg"
    ].copy()
    cols = ["long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
    for col in cols:
        dict["holdings_df_by_period_pct_agg"][col] = (
            dict["holdings_df_by_period_pct_agg"][col]
            / dict["holdings_df_by_period_pct_agg"]["market_value"]
        ) * 100
    LOGGER.info("have $ agg exposures and % agg exposures estimated through time")

    return dict


def plotting_exposures(holdings_by_period_pct_agg: Dict, fund: str, max_date: str):
    # use plotly to create an exposure plot through time
    # Create plotly figure
    # Create figure and add traces
    holdings_df_by_period_pct_agg = holdings_by_period_pct_agg[
        "holdings_df_by_period_pct_agg"
    ]
    fig = go.Figure()
    # Create traces
    fig.add_trace(
        go.Scatter(
            x=holdings_df_by_period_pct_agg.index,
            y=holdings_df_by_period_pct_agg["long_exposure"],
            name="Long Exposure %",
            line=dict(color="green"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=holdings_df_by_period_pct_agg.index,
            y=holdings_df_by_period_pct_agg["short_exposure"],
            name="Short Exposure %",
            line=dict(color="red"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=holdings_df_by_period_pct_agg.index,
            y=holdings_df_by_period_pct_agg["net_exposure"],
            name="Net Exposure %",
            line=dict(color="blue"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=holdings_df_by_period_pct_agg.index,
            y=holdings_df_by_period_pct_agg["gross_exposure"],
            name="Gross Exposure %",
            line=dict(color="orange"),
        )
    )

    # Create layout
    fig.update_layout(
        title="Exposure through Time",
        title_font={"size": 14},
        yaxis=dict(
            title="Exposure %",
            title_font={"size": 10},
            side="left",
            position=0,
            showticklabels=True,
            ticksuffix="",
            showgrid=False,
        ),
        xaxis=dict(
            title="",
            title_font={"size": 10},
            showticklabels=True,
            showgrid=False,
            tickformat="%Y-%m-%d",
            tickmode="linear",
            dtick="M3",
        ),
        legend=dict(
            x=0,
            y=1,
            traceorder="normal",
            bgcolor="rgba(0,0,0,0)",
        ),
        legend_font=dict(size=9),
        autosize=True,
    )
    # Save the plot
    fig.write_html(f"plotting/{fund}_exposure_plotting_through_{max_date}.html")


def plotting_pnl_contributions(
    group_cumul_ret_dict: Dict,
    total_fund_contribution: List,
    fund: str,
    grouping: str,
    periods: List,
    max_date: str,
):
    # Create the stacked bar column plot
    bar_column_list = []
    # Define a list of available colors
    available_colors = [
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "pink",
        "cyan",
        "silver",
        "gold",
        "bronze",
    ]
    # Repeat the available colors to match the length of the list
    num_repeats = (len(group_cumul_ret_dict) // len(available_colors)) + 1
    repeated_colors = available_colors * num_repeats
    # Select the colors based on the length of the list
    colors = repeated_colors[: len(group_cumul_ret_dict)]
    count = 0
    for key, vals in group_cumul_ret_dict.items():
        color = colors[count]
        count += 1
        bar_column_list.append(
            go.Bar(
                x=list(range(len(vals))),
                y=vals,
                name=key,
                marker=dict(color=color),
            )
        )
    # Create the secondary y-axis for cumulative returns as line
    # plots
    layout = go.Layout(
        yaxis=dict(title="Portfolio Contribution", domain=[0, 0.8], tickformat=",.0%"),
        yaxis2=dict(
            title="Cumulative Return",
            domain=[0.85, 1],
            overlaying="y",
            side="right",
            tickformat=",.0%",
        ),
        xaxis=dict(
            title="Date",
            tickvals=list(range(len(vals))),
            ticktext=periods,
        ),
        # barmode='stack',
        title=f"{fund} Portfolio Contribution and Cumulative Return",
    )
    count = 0
    for key, vals in group_cumul_ret_dict.items():
        color = colors[count]
        count += 1
        # Create cumulative return line plots
        bar_column_list.append(
            go.Scatter(
                x=list(range(len(vals))),
                y=vals,
                name=f"{key}_Cumulative Return",
                yaxis="y2",
                line=dict(color=color, width=2),
                mode="lines",
            )
        )
    bar_column_list.append(
        go.Scatter(
            x=list(range(len(total_fund_contribution))),
            y=total_fund_contribution,
            name=f"{fund}_Cumulative Return",
            yaxis="y2",
            line=dict(color="black", width=2),
            mode="lines",
        )
    )
    fig = go.Figure(data=bar_column_list, layout=layout)
    # Save the plot
    fig.write_html(
        f"plotting/{fund}_pnl_contribution_plotting_by_"
        f"{grouping}_through_{max_date}.html"
    )


def convert_to_scaled_min_max(value):
    scale = ""
    if abs(value) >= 1000000:
        # value = value / 1000000
        scale = "M"
        scaler = 1e-6
    elif abs(value) >= 1000:
        # value = value / 1000
        scale = "K"
        scaler = 1e-3
    return scale, scaler


def convert_to_scaled(values: np.ndarray):
    for ix in range(0, values.shape[0]):
        if abs(values[ix]) >= 1000000:
            values[ix] = values[ix] / 1000000
        elif abs(values[ix]) >= 1000:
            values[ix] = values[ix] / 1000
    return values


def plot_bar_chart_exposure(df: pd.DataFrame, max_date: str, fund: str):
    # Calculate the min and max values for scale
    min_scale = df.min().min()
    max_scale = df.max().max()
    num_elements = 7
    # Generate the range of values
    # Create a range of values from min to max
    values = np.linspace(min_scale, max_scale, num_elements)
    values = np.append(values, 0)
    values = np.sort(values)

    # Include zero as an element in the range
    values = np.append(values, 0)

    # Convert the min and max values to scaled format
    if max_scale > abs(min_scale):
        scale, scaler = convert_to_scaled_min_max(max_scale)
    else:
        scale, scaler = convert_to_scaled_min_max(min_scale)

    # # Convert the range of values between min and max values to scaled format
    exposure_values = convert_to_scaled(values)
    formatted_values = [f"${x:.1f} {scale}" for x in exposure_values]
    exposure_values = exposure_values.tolist()

    # Create the horizontal bar column plot using plotly
    fig = go.Figure()

    # Add the bar traces for each column
    df = df.iloc[:, ::-1]
    for i, column in enumerate(df.columns):
        bar_color = "green" if df[column].values[0] >= 0 else "red"
        fig.add_trace(
            go.Bar(
                y=[column],
                x=df[column] * scaler,
                orientation="h",
                name=column,
                marker=dict(color=bar_color),
            )
        )

    # Hide the legend
    fig.update_layout(showlegend=False)

    # Add vertical line
    fig.update_layout(
        shapes=[
            dict(
                type="line",
                x0=0,
                x1=0,
                y0=0,
                y1=len(df.columns),
                line=dict(color="red", width=1),
            )
        ]
    )

    # Set the range and scale for the x-axis
    fig.update_xaxes(
        range=[1.2 * min_scale * scaler, 1.2 * max_scale * scaler], tickformat="$.0f"
    )

    # Set the scale strings for the x-axis scale
    scale_strings = formatted_values
    fig.update_layout(
        annotations=[
            dict(
                x=val,
                y=-0.1,
                text=val_string,
                showarrow=False,
                xref="x",
                yref="paper",  # Set the reference to be the entire figure
                font=dict(family="Arial", size=10),
            )
            for val, val_string in zip(exposure_values, scale_strings)
        ]
    )

    # Set the layout and margins
    fig.update_layout(
        title=f"{fund} Equity and Exposure as of {max_date}",
        xaxis=dict(showticklabels=False),
        yaxis=dict(
            showticklabels=True,
            tickmode="array",
            tickvals=list(range(len(df.columns))),
            ticktext=df.columns,
            tickfont=dict(family="Arial", size=10),
        ),
        margin=dict(l=250, r=250),
        width=800,
        height=500,
    )

    fig.write_html(f"plotting/{fund}_exposure_plotting_as of_{max_date}.html")


def plot_bar_chart_perf_contribution(
    df: pd.DataFrame,
    max_date: str,
    fund: str,
    contribution_grouping: str,
):
    # Set up the figure and axes
    fig = go.Figure()
    if contribution_grouping != "style":
        x_axis_dict = dict(
            tickformat=".2%",  # Format the x-axis labels as percentage with precision 2
            range=[
                -1.2 * min(df[["net"]].max()),
                1.2 * max(df[["net"]].max()),
            ],  # Set the x-axis range
        )
    else:
        x_axis_dict = dict(
            tickformat=".2%",  # Format the x-axis labels as percentage with precision 2
            range=[
                -1.2 * min(df[["contribution"]].max()),
                1.2 * max(df[["contribution"]].max()),
            ],  # Set the x-axis range
        )
    fig.update_layout(
        # barmode='stack',
        # Bar mode is set to 'stack' so that bars are stacked on top of each other
        barmode="relative",  # Set bar mode to 'relative' to have positive and negative bars originate from x=0
        yaxis=dict(
            title=None,  # Remove the label for the y-axis
            tickmode="array",
            tickvals=df[f"{contribution_grouping}"],
            # Use the unique values in 'gics_sector' as tick values
            ticktext=df[f"{contribution_grouping}"]
            # Use the unique values in 'gics_sector' as tick labels
        ),
        xaxis=x_axis_dict,
        shapes=[
            dict(
                type="line",
                xref="x",
                yref="y",
                x0=0,
                x1=0,
                y0=min(df.index),
                y1=max(df.index),
                line=dict(color="black"),
            )
        ],
        title=f"{fund}_Performance Contribution by {contribution_grouping}",  # Add a
        # title to
        # the plot,
        legend=dict(
            orientation="h",  # Set the legend orientation to horizontal
            x=-1,  # Set the x-coordinate of the legend to 0.1
            y=-0.1,  # Set the y-coordinate of the legend to 1.02 (above the plot area)
            traceorder="normal",  # Set the order of the legend items
            bgcolor="rgba(255, 255, 255, 0.5)",  # Set the legend background color with opacity
        ),
        margin=dict(l=250, r=250),
        width=800,
        height=500,
    )

    # Add the bar traces for 'long', 'short', and 'net' columns
    if contribution_grouping != "style":
        fig.add_trace(
            go.Bar(
                name="long",
                x=df["long"],
                y=df[f"{contribution_grouping}"],
                orientation="h",
                marker_color="blue",
            )
        )
        fig.add_trace(
            go.Bar(
                name="short",
                x=df["short"],
                y=df[f"{contribution_grouping}"],
                orientation="h",
                marker_color="orange",
            )
        )
        fig.add_trace(
            go.Bar(
                name="net",
                x=df["net"],
                y=df[f"{contribution_grouping}"],
                base=[0],  # Start the 'net' bars from x=0
                orientation="h",
                marker_color="grey",
                marker_line_color="rgba(0, 0, 0, 0)",
                marker_opacity=0.2,
            )
        )
    else:
        fig.add_trace(
            go.Bar(
                name="contributors",
                x=np.where(df["contribution"] > 0, df["contribution"], np.nan),
                y=df[f"{contribution_grouping}"],
                orientation="h",
                marker_color="blue",
            )
        )
        fig.add_trace(
            go.Bar(
                name="detractors",
                x=np.where(df["contribution"] < 0, df["contribution"], np.nan),
                y=df[f"{contribution_grouping}"],
                orientation="h",
                marker_color="orange",
            )
        )

    fig.write_html(
        f"plotting/{fund}_return_contribution_plotting_by_"
        f"{contribution_grouping}_as of"
        f"_{max_date}.html"
    )


def rename_columns(output_df, style_factors_list_df):
    new_columns = []
    for column in output_df.columns:
        substring = column.split("_")[0]
        match = style_factors_list_df[style_factors_list_df["id"] == substring]
        if not match.empty:
            new_columns.append(match["factor_name"].tolist()[0])
        else:
            new_columns.append(column)

    output_df.columns = new_columns
    return output_df


def convert_to_usd(column):
    return column.apply(lambda x: "${:,.2f}".format(x))


def convert_to_percent(column):
    return column.apply(lambda x: "{:.2%}".format(x))


def convert_to_precision_two(column):
    return column.apply(lambda x: "{:,.2f}".format(x))


def convert_to_precision_zero(column):
    return column.apply(lambda x: "{:,.0f}".format(x))


def calculate_contribution_to_return(portfolio_returns):
    portfolio_weights = portfolio_returns.div(portfolio_returns.sum(axis=1), axis=0)
    # Calculate monthly contribution to return
    monthly_contribution = portfolio_weights * portfolio_returns
    # Calculate cumulative contribution to return
    cumulative_contribution = monthly_contribution.cumsum()

    return cumulative_contribution


def concat_dataframes(df1, df2):
    # Get the number of rows in each dataframe
    num_rows_df1 = df1.shape[0]
    num_rows_df2 = df2.shape[0]

    # Check if the number of rows in each dataframe is the same
    if num_rows_df1 != num_rows_df2:
        raise ValueError("Number of rows in both dataframes must be the same.")
    # Concatenate the dataframes by columns
    df_concat = pd.concat([df1.reset_index(), df2.reset_index()], axis=1)

    return df_concat


def find_two_most_recent_dates(holdings_df: pd.DataFrame) -> str:
    recent_dates = holdings_df["holdings date"].unique()[-2:].min()

    return recent_dates


def calculate_deltas(
    usd_agg: pd.DataFrame, pct_agg: pd.DataFrame, period_calendar: str
) -> pd.DataFrame:
    # Subtract the first value in each column from the second row
    deltas_pct_agg = (pct_agg.iloc[1, :3] - pct_agg.iloc[0, :3]).tolist()
    deltas_usd_agg = (usd_agg.iloc[1, :3] - usd_agg.iloc[0, :3]).tolist()

    # Create a new dataframe with the deltas and the second row values
    attributes = [
        "Long",
        "Short",
        "Net",
        "Gross",
        f"{period_calendar}_chg_net_exposure",
        f"{period_calendar}_chg_long_exposure",
        f"{period_calendar}_chg_short_exposure",
    ]
    usd_agg_df = pd.DataFrame(
        {"Value": usd_agg.iloc[0].tolist() + deltas_usd_agg}, index=attributes
    )
    pct_agg_df = pd.DataFrame(
        {"Percent": pct_agg.iloc[0].tolist() + deltas_pct_agg}, index=attributes
    )
    high_level_current_df = pd.merge(
        usd_agg_df, pct_agg_df, left_index=True, right_index=True
    )

    return high_level_current_df


def color_negative_red(val):
    color = "red" if val < 0 else "black"
    return f"color: {color}"


def calculate_daily_returns(df: pd.DataFrame, stock_list: List):
    nyse = get_calendar("NYSE")
    trading_days = nyse.valid_days(
        start_date=df["date"].min(), end_date=df["date"].max()
    )
    trading_days = trading_days.strftime("%Y-%m-%d")

    result_df = pd.DataFrame(
        columns=["date"] + [stock + "_ret" for stock in stock_list]
    )

    for date in trading_days:
        ret_dict = {}
        for stock in stock_list:
            close = df[(df["date"] == date) & (df["id"] == stock)]["close"].values[0]

            # Find the previous trading day based on the NYSE calendar
            prev_trading_day = None
            prev_day_idx = trading_days.get_loc(date) - 1
            while prev_day_idx >= 0:
                prev_day = trading_days[prev_day_idx]
                if prev_day in trading_days:
                    prev_trading_day = prev_day
                    break
                prev_day_idx -= 1

            # Check if there is data available for the previous trading day
            if prev_trading_day is not None:
                prev_close = df[(df["date"] == prev_trading_day) & (df["id"] == stock)][
                    "close"
                ].values[0]
            else:
                prev_close = np.nan

            # Calculate the daily return
            if np.isnan(prev_close):
                ret = np.nan
            else:
                ret = close / prev_close - 1

            ret_dict[stock + "_ret"] = ret

        result_df.loc[len(result_df)] = [date] + list(ret_dict.values())

    return result_df


def calculate_betas(df: pd.DataFrame):
    betas = {}
    predictors = df.iloc[:, :-1]
    dependent_variable = df.iloc[:, -1]

    X = predictors
    X = sm.add_constant(X)  # add a constant term to the predictors
    model = sm.OLS(dependent_variable, X).fit()
    # Get the beta coefficients
    betas = pd.DataFrame(model.params[1:].values[None, :], columns=df.columns[:-1])

    return betas


def calculate_ratio_multiply(df: pd.DataFrame):
    ratio_multiply = df.copy()
    last_col = df.columns[-1]

    for i in range(len(df)):
        ratio = df.iloc[i, -2] / df.iloc[i, -1]
        ratio_multiply.iloc[i, :-2] = df.iloc[i, :-2] * ratio
    ratio_multiply["adjusted_implied_ret"] = ratio_multiply.iloc[:, :-3].sum(axis=1)

    return ratio_multiply


def calculate_implied_rets(
    betas_df: pd.DataFrame, df_style_rets: pd.DataFrame
) -> pd.DataFrame:
    implied_rets = df_style_rets.copy()

    for column in betas_df.columns:
        implied_rets[column] = betas_df[column].values * df_style_rets["return"]

    implied_rets.rename(columns={"return": "actual_return"}, inplace=True)
    implied_rets["implied_rets"] = implied_rets.iloc[:, :-1].sum(axis=1)
    # Calculate ratio multiply
    implied_rets = calculate_ratio_multiply(implied_rets)

    return implied_rets


def calculate_adjusted_cumulative_returns(df: pd.DataFrame):
    adjusted_cumulative_returns = df.iloc[-1:, :].copy()
    # Calculate cumulative returns for each column
    cumulative_returns = df.cumsum()
    # Calculate the sum of cumulative returns from column 1 through N-1
    sum_cumulative_returns = cumulative_returns.iloc[-1:, :-1].sum(axis=1).values[0]
    #  Calculate the difference between cumulative return of column N and sum cumulative returns
    cumul_diff_actual_v_sum_style = (
        cumulative_returns.iloc[-1:, -1].values[0] - sum_cumulative_returns
    )

    # Calculate the adjusted cumulative returns for each column
    for column in df.columns[:-1]:
        col_cumulative_return = cumulative_returns[column][-1]
        proportion = col_cumulative_return / sum_cumulative_returns
        adjusted_cumulative_returns[column] = col_cumulative_return + (
            cumul_diff_actual_v_sum_style * proportion
        )
    adjusted_cumulative_returns.iloc[-1, -1:] = cumulative_returns.iloc[-1:, -1].values[
        0
    ]
    return adjusted_cumulative_returns


if __name__ == "__main__":
    parser = ArgumentParser(description="")
    parser.add_argument(
        "--fund_list",
        type=str,
        help="list of funds being analyzed",
        default="['Cahill', 'Carruth']",
    )
    parser.add_argument(
        "--run_multi_portfolio_agg",
        type=str,
        help="if set to True, specify list of portfolios across which to agg within "
        "'multi_portfolio_agg_list'",
        default="False",
    )
    parser.add_argument(
        "--multi_portfolio_agg_list",
        type=str,
        help="relevant if 'run_multi_portfolio_agg' is True",
        default="['Dockyard Fund']",
    )
    parser.add_argument(
        "--resample",
        type=str,
        help="if true, user desires to down-sample from daily time series of holdings "
        "to weekly time series of monthly time series of holdings",
        default="True",
    )
    parser.add_argument(
        "--resample_freq",
        type=str,
        help="can be {'W':'Week'} or {'M':'Month'}; depends on desired periodicity of "
        "the holdings-based analysis",
        default="{'M':'Month'}",
    )
    parser.add_argument(
        "--perf_contribution_date_range",
        type=str,
        help="as it sounds, this is a date range over which perf contribution is run",
        default="{'start_date':'2022-12-30', 'end_date': '2023-12-29'}",
    )
    parser.add_argument(
        "--contribution_groupings",
        type=str,
        help="portfolio can be grouped a number of ways; e.g., by long/short, "
        "by industry/sector, etc....",
        default="['long/short', 'gics_sector']",
    )
    parser.add_argument(
        "--top_bottom_contributors",
        type=str,
        help="number of top/bottom N perf contributors to display",
        default=10,
    )
    parser.add_argument(
        "--secrets",
        type=str,
        help="path to secrets file json",
        default="secrets.json",
    )
    args = parser.parse_args()

    # open the fund_list command line argument
    fund_list = args.fund_list
    fund_list = fund_list.replace("'", '"')
    """Note: read-in fund_list via json"""
    fund_list = json.loads(fund_list)

    # open the perf_contribution_date_range command line argument
    perf_contribution_date_range = args.perf_contribution_date_range
    perf_contribution_date_range = perf_contribution_date_range.replace("'", '"')
    """Note: read-in perf_contribution_date_range via json"""
    perf_contribution_date_range = json.loads(perf_contribution_date_range)

    # unpack perf_contribu_date_range
    perf_contribu_start = perf_contribution_date_range["start_date"]
    perf_contribu_end = perf_contribution_date_range["end_date"]

    # open the run_multi_portfolio_agg command line argument
    run_multi_portfolio_agg = args.run_multi_portfolio_agg

    if run_multi_portfolio_agg == "True":
        # open the multi_portfolio_agg_list command line argument
        multi_portfolio_agg_list = args.multi_portfolio_agg_list
        multi_portfolio_agg_list = multi_portfolio_agg_list.replace("'", '"')
        """Note: read-in multi_portfolio_agg_list via json"""

    # open the resample command line argument
    resample = args.resample

    if resample == "True":
        # open the resample_freq command line argument
        resample_freq = args.resample_freq
        resample_freq = resample_freq.replace("'", '"')
        """Note: read-in resample_freq via json"""
        resample_freq = json.loads(resample_freq)
        periodicity = list(resample_freq.keys())[0]
        period_calendar = list(resample_freq.values())[0]

    # open the contribution_groupings command line argument
    contribution_groupings = args.contribution_groupings
    contribution_groupings = contribution_groupings.replace("'", '"')
    """Note: read-in contribution_groupings via json"""
    contribution_groupings = json.loads(contribution_groupings)

    # open the top_bottom_contributors command line argument
    top_bottom_contributors = args.top_bottom_contributors

    # AWS credentials
    with open(args.secrets, "r") as f:
        secrets = json.load(f)

    aws_client = AWSClient(
        aws_access_key_id=secrets["aws_access_key_id"],
        aws_secret_access_key=secrets["aws_secret_access_key"],
        region_name=secrets["aws_region"],
    )

    # 1. structure data
    if run_multi_portfolio_agg == "True":
        fund = None
        holdings_df = pull_portfolio_holdings(
            aws_client, multi_portfolio_agg_list, fund
        )
    else:
        multi_portfolio_agg_list = None
        holdings_df_list = []
        for fund in fund_list:
            holdings_df = pull_portfolio_holdings(
                aws_client, multi_portfolio_agg_list, fund
            )
            holdings_df_list.append(holdings_df)
        holdings_df = pd.concat(holdings_df_list, axis=0)
    holdings_df["date"] = pd.to_datetime(holdings_df["date"])
    holdings_df = holdings_df[
        [col for col in holdings_df.columns if col not in ["t2_symbol", "t2_date"]]
    ]
    holdings_df = holdings_df.rename(columns=lambda x: x.replace("t2_", ""))
    holdings_df.set_index(["date"], inplace=True)
    stock_list = holdings_df["symbol"].unique()
    # Create a trading calendar for the NYSE
    nyse_cal = get_calendar("NYSE")
    nyse_trading_days = nyse_cal.schedule(
        start_date=holdings_df.index.min(), end_date=holdings_df.index.max()
    )
    nyse_tradings_perf_contribution_range = nyse_cal.schedule(
        start_date=perf_contribu_start, end_date=perf_contribu_end
    )

    # need to check whether price is nan
    # if so, need to query prices
    dates_not_in_nyse_tradings_perf_contribution_range = (
        nyse_tradings_perf_contribution_range[
            ~nyse_tradings_perf_contribution_range.isin(nyse_trading_days)
        ]
    )
    if len(dates_not_in_nyse_tradings_perf_contribution_range):
        holdings_df = copy_dataframe(
            holdings_df, dates_not_in_nyse_tradings_perf_contribution_range.index
        )
        holdings_df.index = holdings_df.index.strftime("%Y-%m-%d")
        holdings_df.reset_index(inplace=True)
        min_date = dates_not_in_nyse_tradings_perf_contribution_range.index[0].strftime(
            "%Y-%m-%d"
        )
        max_date = dates_not_in_nyse_tradings_perf_contribution_range.index[
            -1
        ].strftime("%Y-%m-%d")
        portfolio_stock_prices = pull_market_prices(
            aws_client, min_date, max_date, stock_list
        )
        portfolio_stock_prices.rename(columns={"id": "symbol"}, inplace=True)
        holdings_df = pd.merge(
            holdings_df,
            portfolio_stock_prices[["date", "symbol", "close"]],
            on=["date", "symbol"],
            how="inner",
        )
        holdings_df = holdings_df[
            ["date", "symbol", "symbol name", "close"]
            + [
                col
                for col in holdings_df.columns
                if col
                not in [
                    "date",
                    "symbol",
                    "symbol name",
                    "close",
                    "price",
                    "holdings date",
                ]
            ]
        ]
        holdings_df.rename(columns={"close": "price"}, inplace=True)
        holdings_df["mkt val"] = abs(holdings_df["quantity"]) * holdings_df["price"]
        holdings_df["exposure"] = holdings_df["quantity"] * holdings_df["price"]
        holdings_df_grouped = holdings_df.groupby(["date", "portfolio"])
        sum_mkt_val = holdings_df_grouped["mkt val"].transform("sum")
        holdings_df["exposure%"] = holdings_df["exposure"] / sum_mkt_val
        holdings_df["fund mkt val"] = sum_mkt_val
        sum_exposure = holdings_df_grouped["exposure"].transform("sum")
        holdings_df["fund total exposure"] = sum_exposure
        sum_exposure_pct = holdings_df_grouped["exposure%"].transform("sum")
        holdings_df["fund total exposure %"] = 100 * sum_exposure_pct
        holdings_df["holdings date"] = pd.to_datetime(holdings_df["date"]).dt.strftime(
            "%Y%m%d"
        )
        holdings_df.set_index(["date"], inplace=True)
        holdings_df.index = pd.to_datetime(holdings_df.index)

        if np.all(np.isnan(holdings_df["pnl"])):
            # it may be necessary to imply pnl if pnl not found;
            # groupby symbol; order ascending by datetime index; imply pnl as mktval(t)
            # - mktval(t-1)
            # Step 1: Group by symbol
            grouped_df = holdings_df.groupby(["symbol", "fund", "long/short"])
            # Step 2: Sort within each group by datetime index
            sorted_df = grouped_df.apply(lambda group: group.sort_index())
            # Step 3: Calculate periodic pnl within each group
            sorted_df.index = sorted_df.droplevel([0])
            sorted_df["pnl"] = sorted_df.groupby(["symbol", "fund", "long/short"])[
                "mkt val"
            ].diff()
            # Step 4: Update the original DataFrame with calculated pnl
            holdings_df = pd.DataFrame(
                sorted_df.values,
                index=range(0, len(sorted_df)),
                columns=sorted_df.columns,
            )
            holdings_df["date"] = pd.to_datetime(holdings_df["holdings date"])
            holdings_df.set_index(["date"], inplace=True)

            # it may be necessary to imply mtd pnl if pnl not found;
            # Step 1: Group by symbol and month
            holdings_df["pnl"] = pd.to_numeric(holdings_df["pnl"], errors="coerce")
            holdings_df["month"] = holdings_df.index.to_period(
                "M"
            )  # Extract month from datetime index
            grouped = holdings_df.groupby(["symbol", "fund", "long/short", "month"])
            # Step 2: Calculate cumulative sum of 'pnl' within each month
            holdings_df["mtd pnl"] = grouped["pnl"].cumsum()
            # Resetting the added 'month' column as you don't need it anymore
            holdings_df = holdings_df.drop("month", axis=1)

            # it may be necessary to imply ytd pnl if pnl not found;
            # Step 1: Group by symbol and year
            holdings_df["year"] = holdings_df.index.to_period("Y")  # Extract month from
            # datetime index
            grouped = holdings_df.groupby(["symbol", "fund", "long/short", "year"])
            # Step 2: Calculate cumulative sum of 'pnl' within each month
            holdings_df["ytd pnl"] = grouped["pnl"].cumsum()
            # Resetting the added 'year' column as you don't need it anymore
            holdings_df = holdings_df.drop("year", axis=1)

    holdings_df_orig = holdings_df.copy()  # keep the original for daily use later in
    # style analysis
    if resample == "True":
        # Filter the DataFrame to include only NYSE trading days
        filtered_df = holdings_df[
            holdings_df.index.isin(nyse_tradings_perf_contribution_range.index)
        ]
        # Identify the last NYSE trading day in each period [i.e., week; month]
        filtered_df[f"{period_calendar}"] = filtered_df.index.to_period(periodicity)
        holdings_df_filtered = (
            filtered_df[["holdings date", f"{period_calendar}"]]
            .groupby(f"{period_calendar}")
            .last()
        )
        holdings_df = pd.merge(
            holdings_df, holdings_df_filtered, on=["holdings date"], how="right"
        )

    # 2. calculate metrics
    LOGGER.info("estimate exposures and perf contributions")
    # long exposure
    # short exposure
    # net exposure
    # gross exposure
    # security contributions

    max_date = holdings_df["holdings date"].max()  # Get max date in "holdings date"
    if run_multi_portfolio_agg == "True":
        holdings_df_grouped = holdings_df.groupby(["fund"])
        for name, group in holdings_df_grouped:
            fund = name
            # 2.a. aggregate exposures by period and market value by period
            # Group by date and aggregate positive/negative values
            holdings_df_by_period_pct_agg = agg_exposure_by_period(group)
            plotting_exposures(holdings_df_by_period_pct_agg, fund, max_date)
        # now run the agg
        fund = "multi_portfolio_agg"
        holdings_df_by_period_pct_agg = agg_exposure_by_period(holdings_df)
        plotting_exposures(holdings_df_by_period_pct_agg, fund)
    else:
        for fund in fund_list:
            # i) current summary
            recent_dates = find_two_most_recent_dates(holdings_df)
            holdings_df_orig_fund = holdings_df_orig.loc[
                (holdings_df_orig["fund"] == fund)
            ]
            holdings_df_fund = holdings_df.loc[
                (holdings_df["fund"] == fund)
                & (holdings_df["holdings date"] >= recent_dates)
            ]
            holdings_df_by_period_agg = agg_exposure_by_period(holdings_df_fund)
            holdings_df_by_period_usd_agg = holdings_df_by_period_agg[
                "holdings_df_by_period_dollar_agg"
            ]
            holdings_df_by_period_pct_agg = holdings_df_by_period_agg[
                "holdings_df_by_period_pct_agg"
            ]
            cols = ["long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
            holdings_df_by_period_pct_agg_filtered = holdings_df_by_period_pct_agg[
                [col for col in holdings_df_by_period_pct_agg.columns if col in cols]
            ]
            holdings_df_by_period_usd_agg_filtered = holdings_df_by_period_usd_agg[
                [col for col in holdings_df_by_period_usd_agg.columns if col in cols]
            ]
            high_level_stats_summary = calculate_deltas(
                holdings_df_by_period_usd_agg_filtered,
                holdings_df_by_period_pct_agg_filtered,
                period_calendar,
            )
            # append $pnl and $bps
            holdings_df_pnl_by_period = (
                holdings_df[["holdings date", "pnl", "pnl (bps)"]]
                .groupby(["holdings date"])
                .agg(lambda x: x.sum())
            )
            latest_period_pnl = pd.DataFrame(
                holdings_df_pnl_by_period.iloc[-1, :].values[:, None].T,
                columns=[f"$ pnl {period_calendar}", f"$ pnl (bps) {period_calendar}"],
                index=["Basis"],
            )
            # Saving the dataframes to an HTML file
            html_file = (
                f"plotting/{fund}_high_level_summary_stats_as of" f"_{max_date}.html"
            )
            with open(html_file, "w") as f:
                f.write("<html>\n<body>\n")
                f.write("<h1>{}</h1>\n".format(f"Positioning {period_calendar}"))
                f.write(high_level_stats_summary.to_html(justify="left"))
                f.write("<h1>{}</h1>\n".format(f"PnL {period_calendar}"))
                f.write(latest_period_pnl.to_html(justify="left"))
                f.write("</body>\n</html>")

            # ii) exposure plotting
            # agg exposure at portfolio level across time
            holdings_df_fund = holdings_df.loc[holdings_df["fund"] == fund]
            holdings_df_by_period_pct_agg = agg_exposure_by_period(holdings_df_fund)
            plotting_exposures(holdings_df_by_period_pct_agg, fund, max_date)
            # agg exposure at portfolio level most recent date
            holdings_df_by_period_pct_agg["holdings_df_by_period_dollar_agg"].rename(
                columns={"market_value": "equity balance"}, inplace=True
            )
            holdings_df_by_period_filtered = holdings_df_by_period_pct_agg[
                "holdings_df_by_period_dollar_agg"
            ].iloc[-1:, :]
            cols = [
                "equity balance",
                "gross_exposure",
                "long_exposure",
                "short_exposure",
                "net_exposure",
            ]
            holdings_df_by_period_filtered = holdings_df_by_period_filtered[cols]
            holdings_df_by_period_filtered["short_exposure"] = (
                holdings_df_by_period_filtered["short_exposure"] * -1
            )
            plot_bar_chart_exposure(holdings_df_by_period_filtered, max_date, fund)
            # iii) Convert DataFrame to HTML to view portfolio as of latest date
            holdings_df_latest_date = holdings_df[
                holdings_df["holdings date"] == max_date
            ]  # Filter the DataFrame on rows with the maximum date
            holdings_df_latest_date.dropna(axis=1, how="all", inplace=True)
            columns_to_usd = ["mkt val", "exposure", "pnl", "mtd pnl", "ytd pnl"]
            columns_to_usd = [
                header
                for header in columns_to_usd
                if header in holdings_df_latest_date.columns
            ]
            if columns_to_usd:
                holdings_df_latest_date[columns_to_usd] = holdings_df_latest_date[
                    columns_to_usd
                ].apply(convert_to_usd)
            columns_to_pct = ["exposure%"]
            columns_to_pct = [
                header
                for header in columns_to_pct
                if header in holdings_df_latest_date.columns
            ]
            if columns_to_pct:
                holdings_df_latest_date[columns_to_pct] = holdings_df_latest_date[
                    columns_to_pct
                ].apply(convert_to_percent)
            columns_to_precision_two = [
                "price",
                "pnl (bps)",
                "mtd pnl bps",
                "ytd pnl bps",
            ]
            columns_to_precision_two = [
                header
                for header in columns_to_precision_two
                if header in holdings_df_latest_date.columns
            ]
            if columns_to_precision_two:
                holdings_df_latest_date[
                    columns_to_precision_two
                ] = holdings_df_latest_date[columns_to_precision_two].apply(
                    convert_to_precision_two
                )
            columns_to_precision_zero = ["quantity"]
            columns_to_precision_zero = [
                header
                for header in columns_to_precision_zero
                if header in holdings_df_latest_date.columns
            ]
            holdings_df_latest_date[
                columns_to_precision_zero
            ] = holdings_df_latest_date[columns_to_precision_zero].apply(
                convert_to_precision_zero
            )
            # Left justify column headers
            html_table = holdings_df_latest_date.to_html(index=False, justify="left")
            # Save the HTML table to a file
            with open(f"plotting/{fund}_holdings_as of_{max_date}.html", "w") as file:
                file.write(html_table)

            # iv) estimate portfolio contribution through time and performance summary
            # iterate through portfolio at each period end and built matrix of a)
            # portfolio weights and b)
            # a) perf summary
            # perf summary long/short
            cols_to_exclude = []
            for contribution_grouping in contribution_groupings:
                cols_to_include = [
                    "symbol",
                    "symbol name",
                    "mkt val",
                    "exposure",
                    "pnl",
                    "mtd pnl",
                    "ytd pnl",
                    contribution_grouping,
                ]
                # Filter on the max date within 'holdings date'
                filtered_df = holdings_df[holdings_df["holdings date"] == max_date]
                filtered_df.dropna(axis=1, how="all", inplace=True)
                # Group the filtered dataframe by the distinct values in the
                # 'long/short' field
                grouped_df = filtered_df.groupby([contribution_grouping])
                # Iterate over each group
                if "/" in contribution_grouping:
                    contribution_grouping = contribution_grouping.replace("/", "_")
                html_file = (
                    f"plotting/{fund}_perf_summary by {contribution_grouping}_as "
                    f"of"
                    f"_"
                    f"{max_date}.html"
                )
                group_df_list = []
                for name, group in grouped_df:
                    group = group.sort_values(["ytd pnl"], ascending=False)
                    group_df_list.append(group)
                group_df_list = pd.concat(group_df_list, axis=0)
                group_df_list = group_df_list[cols_to_include]
                group_df_list = group_df_list.style.applymap(
                    color_negative_red, subset=["pnl", "mtd pnl", "ytd pnl"]
                ).hide()
                gridline_styles = [
                    {"selector": "table", "props": [("border-collapse", "collapse")]},
                    {
                        "selector": "th, td",
                        "props": [("border", "1px solid lightgray")],
                    },
                ]
                group_df_list.set_table_styles(gridline_styles)
                group_df_list.format(
                    "${:,.2f}",
                    subset=["mkt val", "exposure", "pnl", "mtd pnl", "ytd pnl"],
                )
                with open(html_file, "w") as f:
                    # Saving the dataframes to an HTML file
                    f.write("<html>\n<body>\n")
                    f.write(
                        "<h1>{}</h1>\n".format(
                            f"{fund} perf summary by "
                            f"{contribution_grouping} as of "
                            f"{max_date}"
                        )
                    )
                    f.write(group_df_list.to_html(justify="left", index=False))

            daily_mkt_val_agg_by_fund_date = holdings_df_orig_fund.groupby(
                "holdings " "date"
            )["mkt val"].agg(lambda x: x.sum())
            daily_pnl_agg_by_fund_date = holdings_df_orig_fund.groupby("holdings date")[
                "pnl"
            ].agg(lambda x: x.sum())
            daily_pnl_agg_by_fund_date = pd.DataFrame(
                daily_pnl_agg_by_fund_date.values,
                index=daily_pnl_agg_by_fund_date.index,
                columns=["pnl"],
            )
            daily_mkt_val_agg_by_fund_date = pd.DataFrame(
                daily_mkt_val_agg_by_fund_date.values,
                index=daily_mkt_val_agg_by_fund_date.index,
                columns=["mkt val"],
            )
            daily_mkt_val_agg_by_fund_date_shifted = (
                daily_mkt_val_agg_by_fund_date.shift(1)
            )
            daily_mkt_val_pnl_agg_by_fund_date_merged = pd.merge(
                daily_pnl_agg_by_fund_date,
                daily_mkt_val_agg_by_fund_date_shifted,
                left_index=True,
                right_index=True,
            )
            daily_mkt_val_pnl_agg_by_fund_date_merged["return"] = (
                daily_mkt_val_pnl_agg_by_fund_date_merged["pnl"]
                / daily_mkt_val_pnl_agg_by_fund_date_merged["mkt val"]
            )
            daily_mkt_val_pnl_agg_by_fund_date_merged.index = pd.to_datetime(
                daily_mkt_val_pnl_agg_by_fund_date_merged.index
            ).strftime("%Y-%m-%d")
            mkt_val_agg_by_fund_date = holdings_df_fund.groupby("holdings date")[
                "mkt val"
            ].agg(lambda x: x.sum())
            mtd_pnl_agg_by_fund_date = holdings_df_fund.groupby("holdings date")[
                "mtd pnl"
            ].agg(lambda x: x.sum())
            mkt_val_agg_by_fund_date = pd.DataFrame(
                mkt_val_agg_by_fund_date.values,
                index=mkt_val_agg_by_fund_date.index,
                columns=["mkt val"],
            )
            mkt_val_agg_by_fund_date_shifted = mkt_val_agg_by_fund_date.shift(1)
            holdings_df_fund_grouped_by_date = holdings_df_fund.groupby(
                ["holdings date"]
            )
            count = 0
            holdings_df_fund_list = []
            for name, group in holdings_df_fund_grouped_by_date:
                if count > 0:
                    # estimate pnl % return at security level
                    begin_period_fund_mktval = mkt_val_agg_by_fund_date_shifted.loc[
                        mkt_val_agg_by_fund_date_shifted.index == name[0]
                    ].values[0][0]
                    if resample == "False":
                        group["security_level_contribution"] = (
                            group["pnl"] / begin_period_fund_mktval
                        )
                    else:
                        if periodicity == "M":
                            group["security_level_contribution"] = (
                                group["mtd pnl"] / begin_period_fund_mktval
                            )
                        elif periodicity == "Y":
                            group["security_level_contribution"] = (
                                group["ytd pnl"] / begin_period_fund_mktval
                            )
                    holdings_df_fund_list.append(group)
                count += 1
            holdings_df_fund = pd.concat(holdings_df_fund_list, axis=0)
            for contribution_grouping in contribution_groupings:
                group_contribution_dict = {}
                group_cumul_ret_dict = {}
                group_contribution_list = []
                # create pnl report through time
                # dimensions of pnl visualization are:
                # a)% return period by period [bar-column stacked];
                # Periodic aggregated % portfolio contribution of all long stocks
                # and all short stocks
                # b)cumulative returns over time of each portfolio pnl grouping
                periods = holdings_df_fund["holdings date"].unique().tolist()
                holdings_df_fund_grouping = holdings_df_fund.groupby(
                    ["holdings date", contribution_grouping]
                )
                for name, group in holdings_df_fund_grouping:
                    group_contribution_list.append(
                        [name[0], name[1], group["security_level_contribution"].sum()]
                    )
                data = {
                    f"Column {i + 1}": arg
                    for i, arg in enumerate(group_contribution_list)
                }
                group_contribution_df = pd.DataFrame(data).T
                group_contribution_df = pd.DataFrame(
                    group_contribution_df.values,
                    columns=["holdings date", "grouping", "return"],
                )
                group_contribution_df.reset_index(inplace=True, drop=True)
                for grouping in group_contribution_df["grouping"].unique():
                    group_contribution_dict[f"{grouping}"] = group_contribution_df.loc[
                        group_contribution_df["grouping"] == grouping
                    ]["return"].tolist()
                group_contribution_df_total = (
                    group_contribution_df.groupby(["holdings date"])
                    .agg({"return": "sum"})
                    .reset_index()
                )
                group_contribution_df_total["cumul_ret"] = group_contribution_df_total[
                    "return"
                ].cumsum()
                total_fund_contribution = group_contribution_df_total[
                    "cumul_ret"
                ].tolist()
                # Calculate cumulative group-based returns
                for key, vals in group_contribution_dict.items():
                    group_cumul_ret_dict[f"{key}"] = [
                        sum(vals[: i + 1]) for i in range(len(vals))
                    ]
                if "/" in contribution_grouping:
                    contribution_grouping = contribution_grouping.replace("/", "_")
                plotting_pnl_contributions(
                    group_cumul_ret_dict,
                    total_fund_contribution,
                    fund,
                    contribution_grouping,
                    periods,
                    max_date,
                )
                # c) Top N / bottom N contributors
                # N can be chosen by user
                # top/bottom contributors are run across entire portfolio and within
                # each contribution grouping specified by user [e.g., long/short,
                # sector, industry, etc...]

                top_bottom_contributors_df = holdings_df_fund.groupby(["symbol"]).agg(
                    {"security_level_contribution": "sum"}
                )
                top_bottom_contributors_df_sorted = (
                    top_bottom_contributors_df.sort_values(
                        ["security_level_contribution"], ascending=False
                    )
                )
                top_contributors_df = top_bottom_contributors_df_sorted[
                    :top_bottom_contributors
                ]
                top_contributors_df = pd.DataFrame(
                    top_contributors_df.values,
                    columns=[f"top_{top_bottom_contributors}_perf_contributors"],
                    index=top_contributors_df.index,
                )
                bottom_contributors_df = top_bottom_contributors_df_sorted[
                    -top_bottom_contributors:
                ]
                bottom_contributors_df = pd.DataFrame(
                    bottom_contributors_df.values,
                    columns=[f"bottom_{top_bottom_contributors}_perf_contributors"],
                    index=bottom_contributors_df.index,
                )
                # Concatenate the dataframes
                top_bottom_contributors_df = concat_dataframes(
                    top_contributors_df, bottom_contributors_df
                )
                columns_to_pct = [
                    f"top_{top_bottom_contributors}_perf_contributors",
                    f"bottom_{top_bottom_contributors}_perf_contributors",
                ]
                columns_to_pct = [
                    header
                    for header in columns_to_pct
                    if header in top_bottom_contributors_df.columns
                ]
                if columns_to_pct:
                    top_bottom_contributors_df[
                        columns_to_pct
                    ] = top_bottom_contributors_df[columns_to_pct].apply(
                        convert_to_percent
                    )
                # Save the HTML table to a file
                html_table = top_bottom_contributors_df.to_html(
                    index=False, justify="left"
                )
                with open(
                    f"plotting/{fund}_top_bottom_{top_bottom_contributors}_"
                    f"contributors_through_{max_date}.html",
                    "w",
                ) as file:
                    file.write(html_table)
                LOGGER.info("assess")

            # d) perf contribution by 'long/short' and 'gics_sector'
            grouped_df = (
                holdings_df_fund.groupby(["long/short", "gics_sector"])
                .sum()
                .reset_index()
            )
            # Calculate aggregate security contribution for longs and shorts within
            # each 'gics_sector'
            longs_df = grouped_df[grouped_df["long/short"] == "Long"]
            shorts_df = grouped_df[grouped_df["long/short"] == "Short"]
            # Calculate aggregate security contribution for longs in each 'gics_sector'
            longs_result = (
                longs_df.groupby("gics_sector")["security_level_contribution"]
                .sum()
                .reset_index()
            )
            longs_result.rename(
                columns={"security_level_contribution": "long"}, inplace=True
            )
            # Calculate aggregate security contribution for shorts in each 'gics_sector'
            shorts_result = (
                shorts_df.groupby("gics_sector")["security_level_contribution"]
                .sum()
                .reset_index()
            )
            shorts_result.rename(
                columns={"security_level_contribution": "short"}, inplace=True
            )
            # Merge longs and shorts results to create the final output dataframe
            output_df = longs_result.merge(shorts_result, on="gics_sector", how="outer")
            # Calculate 'net' column
            output_df["short"] = -1 * output_df["short"]
            output_df["net"] = output_df[["long", "short"]].sum(axis=1, skipna=True)
            plot_bar_chart_perf_contribution(output_df, max_date, fund, "gics_sector")

            # e) perf contribution by style
            style_factor_prices = pull_market_prices(
                aws_client, min_date, max_date, style_factors_list["id"].tolist()
            )
            # Example usage
            # Assuming 'df' is your pandas DataFrame with columns 'date', 'id',
            # and 'close'
            # Set the number of rows for each ticker
            n = style_factor_prices["id"].value_counts().min()
            # Sort the DataFrame by 'date'
            style_factor_prices = style_factor_prices.sort_values(by="date")
            # Call the function to calculate daily returns and get only unique dates
            style_factor_rets = calculate_daily_returns(
                style_factor_prices, style_factors_list["id"]
            )
            style_factor_rets.set_index(["date"], inplace=True)
            holdings_df_orig_fund.index = holdings_df_orig_fund.index.strftime(
                "%Y-%m-%d"
            )
            style_factor_rets = pd.merge(
                style_factor_rets,
                daily_mkt_val_pnl_agg_by_fund_date_merged[["return"]],
                left_index=True,
                right_index=True,
            )
            style_factor_rets.dropna(inplace=True)
            # Calculate betas
            betas_df = calculate_betas(style_factor_rets)
            # Create the dictionary
            output_dict = {fund: betas_df}
            implied_rets_df = calculate_implied_rets(betas_df, style_factor_rets)
            # Calculate adjusted cumulative returns
            implied_rets_df = implied_rets_df[
                [
                    col
                    for col in implied_rets_df.columns
                    if col not in ["implied_rets", "adjusted_implied_ret"]
                ]
            ]
            adjusted_cumulative_returns_df = calculate_adjusted_cumulative_returns(
                implied_rets_df
            )
            output_for_style_contribution_plotting = (
                adjusted_cumulative_returns_df.copy()
            )
            # Rename columns in output_for_style_contribution_plotting dataframe based on matching substring in style
            # factors dataframe
            output_for_style_contribution_plotting = rename_columns(
                output_for_style_contribution_plotting, style_factors_list
            )
            output_for_style_contribution_plotting = pd.DataFrame(
                output_for_style_contribution_plotting.T.values,
                index=output_for_style_contribution_plotting.columns,
            ).iloc[:-1, :]
            output_for_style_contribution_plotting.reset_index(inplace=True)
            output_for_style_contribution_plotting.rename(
                columns={"index": "style", 0: "contribution"}, inplace=True
            )
            plot_bar_chart_perf_contribution(
                output_for_style_contribution_plotting, max_date, fund, "style"
            )
            LOGGER.info("style factor data")
