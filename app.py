"""
PortfolioIQ — Flask Backend
Fetches live NSE/BSE stock prices using yfinance (free, no API key needed)

Install dependencies:
    pip install flask flask-cors yfinance

Run:
    python app.py

API will be available at: http://localhost:5000
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from datetime import datetime
import traceback

app = Flask(__name__)
CORS(app)  # Allow your HTML file to call this API

# ── NSE stock list (ticker.NS format for yfinance) ────────────────────────────
NSE_STOCKS = [
    {"ticker": "RELIANCE.NS",   "name": "Reliance Industries",    "sector": "Energy"},
    {"ticker": "TCS.NS",        "name": "Tata Consultancy",        "sector": "IT"},
    {"ticker": "HDFCBANK.NS",   "name": "HDFC Bank",               "sector": "Banking"},
    {"ticker": "INFY.NS",       "name": "Infosys",                 "sector": "IT"},
    {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever",      "sector": "FMCG"},
    {"ticker": "ICICIBANK.NS",  "name": "ICICI Bank",              "sector": "Banking"},
    {"ticker": "KOTAKBANK.NS",  "name": "Kotak Mahindra Bank",     "sector": "Banking"},
    {"ticker": "LT.NS",         "name": "Larsen & Toubro",         "sector": "Infra"},
    {"ticker": "AXISBANK.NS",   "name": "Axis Bank",               "sector": "Banking"},
    {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance",           "sector": "NBFC"},
    {"ticker": "IRCTC.NS",      "name": "IRCTC",                   "sector": "Travel"},
    {"ticker": "ZOMATO.NS",     "name": "Zomato",                  "sector": "Food Tech"},
    {"ticker": "TRENT.NS",      "name": "Trent (Zudio)",           "sector": "Retail"},
    {"ticker": "SBIN.NS",       "name": "State Bank of India",     "sector": "Banking"},
    {"ticker": "NTPC.NS",       "name": "NTPC",                    "sector": "Power"},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors",             "sector": "Auto"},
    {"ticker": "MARUTI.NS",     "name": "Maruti Suzuki",           "sector": "Auto"},
    {"ticker": "SUNPHARMA.NS",  "name": "Sun Pharmaceutical",      "sector": "Pharma"},
    {"ticker": "DRREDDY.NS",    "name": "Dr Reddy's Labs",         "sector": "Pharma"},
    {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel",           "sector": "Telecom"},
    {"ticker": "ITC.NS",        "name": "ITC",                     "sector": "FMCG"},
    {"ticker": "TATASTEEL.NS",  "name": "Tata Steel",              "sector": "Metals"},
    {"ticker": "ADANIGREEN.NS", "name": "Adani Green Energy",      "sector": "Green Energy"},
    {"ticker": "WIPRO.NS",      "name": "Wipro",                   "sector": "IT"},
    {"ticker": "HCLTECH.NS",    "name": "HCL Technologies",        "sector": "IT"},
]


# ── HELPER: fetch single stock ────────────────────────────────────────────────
def fetch_stock(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info   = ticker.fast_info  # faster than .info

        current_price = round(float(info.last_price), 2)
        prev_close    = round(float(info.previous_close), 2)
        change        = round(current_price - prev_close, 2)
        change_pct    = round((change / prev_close) * 100, 2) if prev_close else 0
        volume        = int(info.three_month_average_volume or 0)

        return {
            "ticker":     ticker_symbol.replace(".NS", "").replace(".BO", ""),
            "price":      current_price,
            "prev_close": prev_close,
            "change":     change,
            "change_pct": change_pct,
            "volume":     volume,
            "ok":         True,
        }
    except Exception as e:
        return {"ticker": ticker_symbol, "ok": False, "error": str(e)}


# ── ROUTE: single stock price ─────────────────────────────────────────────────
@app.route("/price")
def price():
    """
    GET /price?ticker=RELIANCE.NS
    Returns: { ticker, price, change, change_pct, prev_close, volume }
    """
    ticker_symbol = request.args.get("ticker", "").upper()
    if not ticker_symbol:
        return jsonify({"error": "ticker parameter required"}), 400

    # Add .NS suffix if not present
    if not ticker_symbol.endswith(".NS") and not ticker_symbol.endswith(".BO"):
        ticker_symbol += ".NS"

    data = fetch_stock(ticker_symbol)
    return jsonify(data)


# ── ROUTE: batch prices ───────────────────────────────────────────────────────
@app.route("/batch")
def batch():
    """
    GET /batch?tickers=TCS,INFY,RELIANCE
    Returns list of price objects for all requested tickers
    """
    raw = request.args.get("tickers", "")
    if not raw:
        return jsonify({"error": "tickers parameter required"}), 400

    tickers = [t.strip().upper() for t in raw.split(",")]
    results = []
    for t in tickers:
        if not t.endswith(".NS") and not t.endswith(".BO"):
            t += ".NS"
        results.append(fetch_stock(t))

    return jsonify({"stocks": results, "count": len(results), "timestamp": datetime.now().isoformat()})


# ── ROUTE: all NSE stocks ─────────────────────────────────────────────────────
@app.route("/market")
def market():
    """
    GET /market
    Returns prices for all 25 NSE stocks in the list above
    Note: this makes 25 requests to yfinance — takes ~5-8 seconds
    """
    results = []
    for stock in NSE_STOCKS:
        data = fetch_stock(stock["ticker"])
        data["name"]   = stock["name"]
        data["sector"] = stock["sector"]
        results.append(data)

    return jsonify({
        "stocks":    results,
        "count":     len(results),
        "timestamp": datetime.now().isoformat()
    })


# ── ROUTE: historical data (for charts) ──────────────────────────────────────
@app.route("/history")
def history():
    """
    GET /history?ticker=TCS.NS&period=6mo
    period options: 1mo, 3mo, 6mo, 1y, 2y, 5y
    Returns: { ticker, dates[], prices[], change_pct_overall }
    """
    ticker_symbol = request.args.get("ticker", "").upper()
    period        = request.args.get("period", "6mo")

    if not ticker_symbol:
        return jsonify({"error": "ticker parameter required"}), 400

    if not ticker_symbol.endswith(".NS") and not ticker_symbol.endswith(".BO"):
        ticker_symbol += ".NS"

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist   = ticker.history(period=period)

        dates  = [str(d.date()) for d in hist.index]
        prices = [round(float(p), 2) for p in hist["Close"]]

        overall_chg = 0
        if len(prices) >= 2:
            overall_chg = round(((prices[-1] - prices[0]) / prices[0]) * 100, 2)

        return jsonify({
            "ticker":          ticker_symbol.replace(".NS", ""),
            "period":          period,
            "dates":           dates,
            "prices":          prices,
            "change_pct_total": overall_chg,
            "data_points":     len(prices),
        })
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


# ── ROUTE: NIFTY 50 index ─────────────────────────────────────────────────────
@app.route("/indices")
def indices():
    """
    GET /indices
    Returns current NIFTY 50 and SENSEX levels
    """
    results = {}
    for name, symbol in [("NIFTY50", "^NSEI"), ("SENSEX", "^BSESN")]:
        try:
            t = yf.Ticker(symbol)
            fi = t.fast_info
            results[name] = {
                "price":      round(float(fi.last_price), 2),
                "prev_close": round(float(fi.previous_close), 2),
                "change_pct": round((fi.last_price - fi.previous_close) / fi.previous_close * 100, 2),
            }
        except Exception as e:
            results[name] = {"error": str(e)}

    return jsonify(results)


# ── ROUTE: health check ───────────────────────────────────────────────────────
@app.route("/")
def health():
    return jsonify({
        "status":  "PortfolioIQ API running ✅",
        "version": "1.0",
        "endpoints": ["/price", "/batch", "/market", "/history", "/indices"]
    })


if __name__ == "__main__":
    print("\n🚀 PortfolioIQ API starting...")
    print("📡 Endpoints available at http://localhost:5000")
    print("   GET /price?ticker=RELIANCE.NS")
    print("   GET /batch?tickers=TCS,INFY,ZOMATO")
    print("   GET /market  (all 25 NSE stocks)")
    print("   GET /history?ticker=TCS.NS&period=6mo")
    print("   GET /indices (NIFTY 50, SENSEX)\n")
    app.run(debug=True, port=5000)
