import time
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

LSE = "SHEL.L"
AMS = "SHELL.AS"
FX  = "EURGBP=X"
PRIMARY_INTERVAL, PRIMARY_PERIOD   = "1m", "7d"
FALLBACK_INTERVAL, FALLBACK_PERIOD = "5m", "60d"
K = 1e6
CACHE_CSV = "dual_list_cache.csv"

def dl_with_retry(tickers, interval, period, tries=6, sleep0=2.0):
    for i in range(tries):
        try:
            df = yf.download(
                tickers=tickers,
                interval=interval,
                period=period,
                auto_adjust=False,
                progress=False,
                group_by="ticker",
                threads=False,
            )
            if df is not None and not df.empty:
                return df
        except Exception as e:
            err = str(e)
        time.sleep(sleep0 * (2 ** i))
    raise RuntimeError(f"Download failed after {tries} tries. Last error: {err if 'err' in locals() else 'n/a'}")

def flatten_cols(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["|".join([str(c) for c in col if c]) for col in df.columns]
    return df

def get_price(df, ticker, field="Close"):
    if f"{ticker}|{field}" in df.columns:
        return df[f"{ticker}|{field}"]
    if field in df.columns and len(df.columns) <= 6:
        return df[field]
    if f"{ticker} Close" in df.columns:
        return df[f"{ticker} Close"]
    raise KeyError(f"Cannot find {field} for {ticker}. Columns: {list(df.columns)[:8]}...")

def get_vol(df, ticker):
    if f"{ticker}|Volume" in df.columns:
        return df[f"{ticker}|Volume"]
    if "Volume" in df.columns and len(df.columns) <= 6:
        return df["Volume"]
    if f"{ticker} Volume" in df.columns:
        return df[f"{ticker} Volume"]
    raise KeyError(f"Cannot find Volume for {ticker}. Columns: {list(df.columns)[:8]}...")

if CACHE_CSV:
    try:
        df_all = pd.read_csv(CACHE_CSV, parse_dates=["Datetime"], index_col="Datetime")
    except Exception:
        df_all = None
else:
    df_all = None

if df_all is None or df_all.empty:
    try:
        raw = dl_with_retry([LSE, AMS, FX], PRIMARY_INTERVAL, PRIMARY_PERIOD)
    except RuntimeError:
        raw = dl_with_retry([LSE, AMS, FX], FALLBACK_INTERVAL, FALLBACK_PERIOD)
    raw = flatten_cols(raw)
    raw.index = raw.index.tz_convert("UTC") if raw.index.tz is not None else raw.index.tz_localize("UTC")
    df_all = raw.copy()
    if CACHE_CSV:
        df_all.to_csv(CACHE_CSV, index_label="Datetime")

freq = "T" if "1m" in (PRIMARY_INTERVAL, FALLBACK_INTERVAL) and "1m" in str(df_all.index.freq or "") else None
if freq is None:
    step = (df_all.index[1] - df_all.index[0]).seconds // 60 if len(df_all) > 1 else 5
    freq = "5T" if step >= 5 else "T"

fx_close = get_price(df_all, FX, "Close").asfreq(freq).ffill()

lse_close = get_price(df_all, LSE, "Close")
ams_close_eur = get_price(df_all, AMS, "Close")
lse_vol = get_vol(df_all, LSE)
ams_vol = get_vol(df_all, AMS)

df = pd.concat([lse_close, lse_vol, ams_close_eur, ams_vol, fx_close], axis=1)
df.columns = ["LSE_Close", "LSE_Vol", "AMS_Close_EUR", "AMS_Vol", "EURGBP"]
df = df.dropna()

df = df.between_time("08:00", "16:30")

df["AMS_Close_GBP"] = df["AMS_Close_EUR"].astype(float) * df["EURGBP"].astype(float)
df["DeltaP"] = df["LSE_Close"] - df["AMS_Close_GBP"]
mid = 0.5 * (df["LSE_Close"] + df["AMS_Close_GBP"])
df["DeltaP_bps"] = 1e4 * df["DeltaP"] / mid

vol_sum = (df["LSE_Vol"].fillna(0) + df["AMS_Vol"].fillna(0)).replace(0, np.nan)
df["Alpha"] = K / vol_sum
df = df.dropna(subset=["Alpha", "DeltaP"])

df["q_star"] = df["DeltaP"] / (2.0 * df["Alpha"])
df["pi_star"] = (df["DeltaP"]**2) / (4.0 * df["Alpha"])

print("Rows kept:", len(df))
print("Mean ΔP (GBP):", df["DeltaP"].mean())
print("Mean ΔP (bps):", df["DeltaP_bps"].mean())
print("Median q*:", df["q_star"].median())
print("Median π*:", df["pi_star"].median())

plt.figure(figsize=(10,4))
df["DeltaP_bps"].plot(title="Price difference ΔP_t (bps)")
plt.xlabel("Time (UTC)"); plt.ylabel("bps"); plt.tight_layout(); plt.show()

plt.figure(figsize=(6,6))
plt.scatter(df["DeltaP"], df["q_star"], s=6, alpha=0.4)
plt.xlabel("Mispricing ΔP_t (GBP)"); plt.ylabel("Optimal trade size q*_t (model units)")
plt.title("Mispricing vs Optimal Trade Size"); plt.tight_layout(); plt.show()

plt.figure(figsize=(10,4))
df["pi_star"].dropna().plot(kind="hist", bins=60, title="Distribution of model profit π*_t")
plt.xlabel("GBP (model units)"); plt.tight_layout(); plt.show()

df.to_csv("dual_list_results.csv", index_label="Datetime")

# Thanks for reading my terrible code