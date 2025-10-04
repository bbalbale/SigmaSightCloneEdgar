import json
import logging
from argparse import ArgumentParser
from datetime import datetime

import pandas as pd
import yfinance as yf

from apis.polygon_dcm import POLYGON
from database_dockyard_capital_mgmt import AWSClient

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Function to get GICS sector and industry data for a stock using yfinance
market_type = "stocks"
now = datetime.utcnow()
run_date = now.strftime("%Y%m%d")


def get_gics_data(symbol):
    try:
        # Create a YahooFinanceTicker object with the stock symbol
        ticker = yf.Ticker(symbol)

        # Get the sector and industry information
        gics_data = ticker.info
        gics_sector = gics_data["sector"]
        gics_industry = gics_data["industry"]

        # Print the results
        df = pd.DataFrame(
            {
                "run_date": [run_date],
                "symbol": [symbol],
                "gics sector": [gics_sector],
                "gics industry": [gics_industry],
            }
        )
        return df
    except Exception as e:
        print(f"Error occurred: {e}")


parser = ArgumentParser(description="")
parser.add_argument(
    "--secrets",
    type=str,
    help="path to secrets file json",
    default="secrets.json",
)
args = parser.parse_args()

with open(args.secrets, "r") as f:
    secrets = json.load(f)

aws_client = AWSClient(
    aws_access_key_id=secrets["aws_access_key_id"],
    aws_secret_access_key=secrets["aws_secret_access_key"],
    region_name=secrets["aws_region"],
)

# Function to get tickers for all US listed equities
# get tickers
polygon_api = POLYGON(secrets["polygon_api_key"])
tickers = polygon_api.pull_tickers(market_type)

count = 0
gics_classification_list = []
for ticker in tickers:
    count += 1
    # Call the function with a stock symbol to get the GICS data
    LOGGER.info(
        f"processing {ticker} which is number {count} out of "
        f"a total of {len(tickers)}"
    )
    gics_classification = get_gics_data(ticker)

    # 2. post-process the concatenated list of dataframes

    if gics_classification is not None:
        key_cols = ["symbol", "gics sector", "gics industry"]
        partition_cols = ["run_date"]
        # put to db
        aws_client.merge_into_dataset(
            data=gics_classification,
            partition_cols=partition_cols,
            key_cols=key_cols,
            data_dir="gics_classification",
        )
