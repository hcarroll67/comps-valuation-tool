import yfinance as yf
import pandas as pd

# 1. CONFIG
TARGET = "SHEL"                     # Shell
PEERS = ["BP", "XOM", "CVX", "TTE"]  # BP, ExxonMobil, Chevron, TotalEnergies

VALUATION_METRICS = ["P/E", "Fwd P/E", "EV/EBITDA", "P/B"]

# 2. FETCH
def _normalize_yield(value):
    # Yahoo's dividend yield field is sometimes a fraction (0.041), sometimes already a percentage (4.1)
    if value is None:
        return None
    return value * 100 if value < 1 else value

def fetch_metrics(ticker: str) -> dict:
    info = yf.Ticker(ticker).info

    ev = info.get("enterpriseValue")
    ebitda = info.get("ebitda")
    ev_ebitda = (ev / ebitda) if (ev and ebitda) else None

    return {
        "Ticker": ticker,
        "Name": info.get("shortName", ticker),
        "P/E": info.get("trailingPE"),
        "Fwd P/E": info.get("forwardPE"),
        "EV/EBITDA": ev_ebitda,
        "P/B": info.get("priceToBook"),
        "Div Yield %": _normalize_yield(info.get("dividendYield")),
    }

# 3. COMPS TABLE
def build_comps_table(target: str, peers: list) -> pd.DataFrame:
    rows = [fetch_metrics(t) for t in [target] + peers]
    df = pd.DataFrame(rows).set_index("Ticker")
    return df

def add_peer_comparison(df: pd.DataFrame, target: str):
    all_metrics = VALUATION_METRICS + ["Div Yield %"]
    peer_rows = df.drop(index=target)
    peer_avg = peer_rows[all_metrics].mean(numeric_only=True)

    df = df.copy()
    avg_row = {"Name": "-"}
    avg_row.update({m: peer_avg[m] for m in all_metrics})
    df.loc["Peer Average"] = avg_row

    target_row = df.loc[target]

    # % premium/discount for valuation multiples (higher = more expensive)
    premium = {}
    for metric in VALUATION_METRICS:
        t_val, p_val = target_row[metric], peer_avg[metric]
        if pd.notna(t_val) and pd.notna(p_val) and p_val != 0:
            premium[metric] = (t_val / p_val - 1) * 100
        else:
            premium[metric] = None

    # Plain difference for dividend yield (not a premium/discount concept)
    t_yield, p_yield = target_row["Div Yield %"], peer_avg["Div Yield %"]
    yield_diff = (t_yield - p_yield) if (pd.notna(t_yield) and pd.notna(p_yield)) else None

    return df, premium, yield_diff

# 4. REPORT
def print_report(df: pd.DataFrame, premium: dict, yield_diff, target: str):
    print(f"\nRelative Valuation — {target} vs. Peer Set")
    print("=" * 65)
    print(df.round(2).to_string())

    print("\nTarget vs. Peer Average (valuation multiples):")
    for metric, pct in premium.items():
        if pct is None:
            print(f"  {metric}: data unavailable")
            continue
        direction = "premium" if pct > 0 else "discount"
        print(f"  {metric}: {pct:+.1f}%  ({direction} to peer average)")

    print("\nDividend Yield vs. Peer Average:")
    if yield_diff is None:
        print("  data unavailable")
    else:
        direction = "higher" if yield_diff > 0 else "lower"
        print(f"  {yield_diff:+.2f} percentage points {direction} than peer average")


if __name__ == "__main__":
    comps = build_comps_table(TARGET, PEERS)
    comps, premium, yield_diff = add_peer_comparison(comps, TARGET)
    print_report(comps, premium, yield_diff, TARGET)
