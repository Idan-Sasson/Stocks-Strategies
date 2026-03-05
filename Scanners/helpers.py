import pandas as pd
import time
import yfinance as yf


def filter_daily_volume(df, threshold, per_dollar=False):
    """
    Filters out tickers whose daily median volume is less than threshold
    df - dataFrame
    threshold - int/float minimum volume to filter above
    per_dollar - boolean - True if to filter by volume x price, False filter by volume
    returns the new dataframe
    """
    if per_dollar: 
        vol_mask = (df["Volume"] * df["Close"]).median() >= threshold
    else:
        vol_mask = df["Volume"].median() >= threshold
    tickers = vol_mask[vol_mask].index
    return df.loc[:, (slice(None), tickers)]


def drop_nan_days(df, column, threshold):
    """
    Drops tickers whose nan values in the column % are higher than threshold
    df - DataFrame
    column - string name of column (for example Close)
    threshold - percentage
    """
    col_data = df[column]
    nan_pct = col_data.isna().mean() * 100
    tickers = nan_pct[nan_pct < threshold].index
    return df.loc[:, (slice(None), tickers)]


def filter_tickers(df, tickers):
    if isinstance(tickers, str):
        tickers = [tickers]
    return df.loc[:, df.columns.get_level_values(1).isin(tickers)]

def get_all_us_tickers():
    """
    Returns a list of all US traded tickers
    """
    nasdaq_url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    other_url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
    nq_df = pd.read_csv(nasdaq_url, sep='|', on_bad_lines='skip')
    ot_df = pd.read_csv(other_url, sep='|', on_bad_lines='skip')
    ot_df.rename(columns={"NASDAQ Symbol": "Symbol"}, inplace=True)

    df = pd.concat([nq_df, ot_df], ignore_index=True)
    df.drop_duplicates(subset=["Symbol"], inplace=True)

    # Filter out ETF, test stocks and NaNs
    df = df[(df["ETF"] == "N") & (df["Test Issue"] == "N")].dropna(subset=["Symbol"])["Symbol"].tolist()
    return df


def get_data(tickers_list, period="max", interval="1d", start=None, end=None, timeout=20, print_progress=True, batch_size=200):
    """
    Divides the tickers_list into batches so it'll download each batch sepertly then combines into a full dataset
    tickers_list: list,  list of tickers
    periood: str, Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    interval: STR, Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo Intraday data cannot extend last 60 days 
    start: str, Download start date string (YYYY-MM-DD) or datetime
    end: str, Download end date string (YYYY-MM-DD) or datetime

    """
    batches = []
    for i in range(0, len(tickers_list), batch_size):
        batches.append(tickers_list[i: i+batch_size])
    res = []
    i = 0
    for batch in batches:
        if print_progress:
            print(f"Batch {i}/{len(batches)}")
        i += 1
        while True:
            yf.shared._ERRORS = {}
            failed_tickers = []
            timeout_tickers = []
            if start:
                batch_res = yf.download(batch, start=start, end=end, interval=interval, group_by='column', )
            else:
                batch_res = yf.download(batch, period=period, interval=interval, group_by='column')
            errors = yf.shared._ERRORS
            for ticker in errors:
                if errors[ticker].startswith("YFRateLimitError"):
                    failed_tickers.append(ticker)
                elif errors[ticker].startswith("Timeout"):
                    timeout_tickers.append(ticker)
            batch_res.drop(columns=failed_tickers, level=1, inplace=True, errors="ignore")
            res.append(batch_res)
            batch = failed_tickers + timeout_tickers
            if (not batch):
                break
            if failed_tickers:
                print(f"Too many requests: Sleeping {timeout} seconds")
                time.sleep(timeout)
    return pd.concat(res, axis=1)