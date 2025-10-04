import json
import logging
from argparse import ArgumentParser
from datetime import datetime, timedelta
import os
import pandas as pd
import numpy as np
import re
from database_dockyard_capital_mgmt import AWSClient
import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

now = datetime.utcnow()
# end_date = now.strftime("%Y%m%d")
end_date = "20231224"

if __name__ == "__main__":
    parser = ArgumentParser(description="")
    parser.add_argument(
        "--run_new_holdings_concat",
        type=str,
        help="set to True if need to concatenate holdings across time; otherwise, "
        "False -- main reason to set as False if developing new features of how "
        "to process the data and don't want to wait for creation of list of "
        "dataframes during each code iteration",
        default="True",
    )
    parser.add_argument(
        "--years",
        type=str,
        help="the years over which holdings are to be loaded to db",
        default="[2021, 2022, 2023]",
    )
    parser.add_argument(
        "--secrets",
        type=str,
        help="path to secrets file json",
        default="secrets.json",
    )
    args = parser.parse_args()

    # open the run_new_holdings_concat command line argument
    run_new_holdings_concat = args.run_new_holdings_concat

    # open the years command line argument
    years = args.years
    years = years.replace("'", '"')
    """Note: read-in years via json"""
    years = json.loads(years)

    with open(args.secrets, "r") as f:
        secrets = json.load(f)

    # get tickers
    aws_client = AWSClient(
        aws_access_key_id=secrets["aws_access_key_id"],
        aws_secret_access_key=secrets["aws_secret_access_key"],
        region_name=secrets["aws_region"],
    )

    # 1. get data from files
    # define file path
    if run_new_holdings_concat == "True":
        excel_data = []
        for year in years:
            count = 0
            directory = f"data/{year}/Daily Flash"
            for file in os.listdir(directory):
                file_list = os.listdir(directory)
                if file.endswith(".xls") or file.endswith(".xlsx"):
                    file_path = os.path.join(directory, file)
                    match = re.search(r"\d{2}\d{2}\d{4}", file)
                    if match:
                        matched_value = match.group()
                        matched_value = datetime.strptime(matched_value, "%m%d%Y")
                        matched_value = matched_value.strftime("%Y-%m-%d")
                    else:
                        match = re.search(r"\d{2}\d{2}", file)
                        matched_value = match.group()
                        matched_value = f"{matched_value}{year}"
                        matched_value = datetime.strptime(matched_value, "%m%d%Y")
                        matched_value = matched_value.strftime("%Y-%m-%d")
                    holdings_file = pd.read_excel(file_path)
                    holdings_file.columns = holdings_file.columns.str.lower()
                    holdings_file["holdings date"] = matched_value
                    holdings_file = holdings_file[
                        ["holdings date"]
                        + [
                            col
                            for col in holdings_file.columns
                            if col not in ["holdings date", "long/short"]
                        ]
                    ]
                    holdings_file = holdings_file.loc[
                        :, ~holdings_file.columns.str.contains("^unnamed")
                    ]
                    if "symbol" not in holdings_file or ("qty" not in holdings_file
                                                         and "quantity" not in
                                                         holdings_file):
                        LOGGER.info(f"holdings as of {matched_value} are missing "
                                    f"either Symbol field or Qty field and those "
                                    f"holdings are therefore not processed further "
                                    f"and will not go to DB")
                        continue
                    holdings_file.dropna(subset=["symbol", "qty"], inplace=True)
                    if "startmktval(v)" in holdings_file:
                        holdings_file.rename(
                            columns={"startmktval(v)": "mkt val"}, inplace=True
                        )
                    elif "mktval(v)" in holdings_file:
                        holdings_file.rename(
                            columns={"mktval(v)": "mkt val"}, inplace=True
                        )
                    if "symbollongname" in holdings_file:
                        holdings_file.rename(
                            columns={"symbollongname": "symbol name"}, inplace=True
                        )
                    elif "symbollongname" not in holdings_file and "symbol" not in \
                            holdings_file:
                        holdings_file["symbol name"] = np.nan
                    if "lastprc(v)" in holdings_file:
                        holdings_file.rename(
                            columns={"lastprc(v)": "price"}, inplace=True
                        )
                    if "qty" in holdings_file:
                        holdings_file.rename(
                            columns={"qty": "quantity"}, inplace=True
                        )
                    if "exposure(v)" in holdings_file:
                        holdings_file.rename(
                            columns={"exposure(v)": "exposure"}, inplace=True
                        )
                    if "pl(v)" in holdings_file:
                        holdings_file.rename(
                            columns={"pl(v)": "pnl"}, inplace=True
                        )
                    if "plbps" in holdings_file:
                        holdings_file.rename(
                            columns={"plbps": "pnl (bps)"}, inplace=True
                        )
                    if "mtdpl(v)" in holdings_file:
                        holdings_file.rename(
                            columns={"mtdpl(v)": "mtd pnl"}, inplace=True
                        )
                    if "mtdplbps" in holdings_file:
                        holdings_file.rename(
                            columns={"mtdplbps": "mtd pnl bps"}, inplace=True
                        )
                    elif "mtdplbps" not in holdings_file:
                        holdings_file["mtd pnl bps"] = np.nan
                    if "ytdpl(v)" in holdings_file:
                        holdings_file.rename(
                            columns={"ytdpl(v)": "ytd pnl"}, inplace=True
                        )
                    elif "ytdpl(v)" not in holdings_file:
                        holdings_file["ytd pnl"] = np.nan
                    if "ytdplbps" in holdings_file:
                        holdings_file.rename(
                            columns={"ytdplbps": "ytd pnl bps"}, inplace=True
                        )
                    elif "ytdplbps" not in holdings_file:
                        holdings_file["ytd pnl bps"] = np.nan
                    if "portfolio" not in holdings_file:
                        holdings_file["portfolio"] = "Dockyard Fund"
                    if "strategy" not in holdings_file:
                        holdings_file["strategy"] = np.nan
                    if "mtdpl(b)" not in holdings_file:
                        holdings_file["mtdpl(b)"] = np.nan
                    if "ytdpl(b)" not in holdings_file:
                        holdings_file["ytdpl(b)"] = np.nan
                    # if "exposure%" not in holdings_file:
                    fund_mktval = holdings_file["mkt val"].sum()
                    holdings_file["exposure%"] = holdings_file[
                        "exposure"
                    ] / fund_mktval
                    holdings_file["long/short"] = np.where(
                        holdings_file["quantity"] < 0, "Short", "Long"
                    )
                    holdings_file = holdings_file[
                        ["holdings date","symbol","symbol name"]
                        + [
                            col
                            for col in holdings_file.columns
                            if col not in ["holdings date","symbol","symbol name"]
                        ]
                    ]
                    holdings_date = holdings_file['holdings date'].iloc[0]
                    removal_list =  ['symbolmtdplbps', 'includes closed positions',
                                     'incomeexpense']
                    columns_to_keep = [col for col in holdings_file.columns if not
                        any(substring in col for substring in removal_list)]
                    holdings_file = holdings_file[columns_to_keep]
                    columns_to_str = ["holdings date", "symbol", "symbol name",
                                          "strategy","portfolio", "long/short"]
                    columns_to_float = [col for col in holdings_file.columns if
                                          col not in columns_to_str]
                    holdings_file = holdings_file.replace({',': '', '\+|-': '', '\.': ''},
                                             regex=True)
                    holdings_file[columns_to_float] = holdings_file[
                        columns_to_float].astype(
                        float)
                    holdings_file[columns_to_str] = holdings_file[
                        columns_to_str].astype(
                        str)
                    if count > 0 or year != years[0]:
                        holdings_file = holdings_file[excel_data[0].columns]
                    excel_data.append(holdings_file)
                    count += 1

                    LOGGER.info(
                        f"processing report number {count} out of total "
                        f"{len(file_list)} reports in year {year} and "
                        f"holdings date of {holdings_date}"
                    )
        excel_data_df_list = pd.concat(excel_data, axis=0)
        LOGGER.info("need to post-process the concatenated file")
        excel_data_df_list.to_csv(f"data/multi_year_holdings_{end_date}.csv")
    else:
        excel_data_df_list = pd.read_csv(f"data/multi_year_holdings_{end_date}.csv")
        excel_data_df_list = excel_data_df_list.loc[
                        :, ~excel_data_df_list.columns.str.contains("^Unnamed")
                        ]

    # Aggregate pnl of portfolio holdings from position level to portfolio level
    # every day
    df_positions = excel_data_df_list.copy()
    df_portfolio_pnl = df_positions.groupby('holdings date')['pnl'].sum()

    # Aggregate mkt val of portfolio holdings from position level to portfolio level
    # every day
    df_portfolio_mkt_val = df_positions.groupby('holdings date')['mkt val'].sum()

    # 2. post-process the concatenated list of dataframes

    key_cols = ["symbol", "quantity"]
    # put to db
    aws_client.merge_into_dataset(
        data=excel_data_df_list,
        partition_cols=["portfolio","holdings date"],
        key_cols=key_cols,
        data_dir=f"portfolio_holdings"
    )
