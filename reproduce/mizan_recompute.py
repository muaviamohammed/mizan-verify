#!/usr/bin/env python3
"""
MIZAN — independent recomputation of a disclosed credential, from scratch.

The point: you should not have to trust MIZAN's verifier binary to know the
engine's arithmetic is honest. This script re-implements the in-circuit
backtest (mizan-core, guest v10) in ~200 lines of plain Python — integer
arithmetic faithfully mirrored (Rust i128 semantics, truncating division) —
and reproduces every committed number of the DISCLOSED strategy below from
the pinned dataset alone.

Disclosed strategy (public on purpose — it exists so you can recompute):
    Donchian(36) breakout, regime SMA(40), long-only, leverage 1.00x,
    fee 7bp + slippage 3bp per side, dataset btc_daily.csv (1,096 bars).

Engine ground truth (printed by `host --prove`, committed in the credential):
    Sharpe 0.75 | OOS 1.10 | MaxDD 16.16% | net +47.6% | CAGR 13.9%
    worst-bar -13.54% | trades 65 | bars-in-market 129 | verdict FAIL

Run:  python3 mizan_recompute.py [path/to/btc_daily.csv]
No dependencies beyond the standard library. Crosswalk to the Rust source
in CROSSWALK.md (file:line for every formula below).
"""
import csv, math, sys

# ── constants (mizan-core/src/lib.rs) ───────────────────────────────────────
EQUITY_SCALE   = 100_000_000        # 1e8 = 1.0 equity
CBPS_PER_X1    = 1_000_000          # centibps in 1.0x
MIN_DAILY_CBPS = -1_000_000         # -100% per-bar clamp
MAX_DAILY_CBPS = 1_000_000_000
MAX_LEV_X100   = 10_000
OOS_NUM, OOS_DEN = 3, 10            # OOS = last 30% of bars
MAX_EQUITY     = (1 << 100)         # engine caps far above anything reachable

def tdiv(a, b):
    """Rust integer division truncates toward zero; Python floors. Mirror Rust."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q

def isqrt(v):
    return math.isqrt(v) if v >= 0 else 0

# ── load pinned data (micro-units x1e6, exactly like host parse_bars) ──────
def load(path):
    close, low, high = [], [], []
    with open(path) as f:
        for row in list(csv.reader(f))[1:]:
            if len(row) < 5: continue
            mu = lambda x: int(round(float(x) * 1_000_000))
            high.append(mu(row[2])); low.append(mu(row[3])); close.append(mu(row[4]))
    return close, low, high

# ── signals: Donchian(36) breakout + regime SMA(40), long-only ─────────────
def signals(prices, don=36, regime=40):
    n = len(prices)
    sig = [0] * n
    for i in range(don, n):                      # close > max of PRIOR `don` closes
        sig[i] = 1 if prices[i] > max(prices[i - don:i]) else 0
    out, rsum = [0] * n, 0
    for i in range(n):                           # sliding-sum SMA, integer floor
        rsum += prices[i]
        if i >= regime: rsum -= prices[i - regime]
        long_ok = (i + 1 >= regime) and (prices[i] > tdiv(rsum, regime))
        out[i] = 1 if (sig[i] >= 1 and long_ok) else 0
    return out

# ── the backtest core (backtest_signals_dynlev, lib.rs:3301) ───────────────
def bar_net_cbps(pos, prev, lev, p0, p1, cost_cbps):
    if pos != 0 and p0 != 0:
        unit = max(MIN_DAILY_CBPS, min(MAX_DAILY_CBPS, tdiv((p1 - p0) * CBPS_PER_X1, p0)))
        gross = tdiv(pos * lev * unit, 100)
    else:
        gross = 0
    cost = tdiv(cost_cbps * lev, 100) * abs(pos - prev) if pos != prev else 0
    lo = tdiv(MIN_DAILY_CBPS * lev, 100) - cost_cbps * lev
    return max(lo, min(MAX_DAILY_CBPS, gross - cost))

def backtest(sig, close, low, high, cost_bps=10, ppy=365, lev_x100=100):
    n = len(close)
    equity, peak = EQUITY_SCALE, EQUITY_SCALE
    max_dd_bps, worst_cbps, trades, in_mkt = 0, 0, 0, 0
    sum_r, rets, rets_bps, prev = 0, [], [], 0
    cost_cbps = cost_bps * 100
    for t in range(1, n):
        pos, lev = sig[t - 1], max(1, min(MAX_LEV_X100, lev_x100))
        if pos != 0: in_mkt += 1
        if pos != prev and pos != 0: trades += 1
        net = bar_net_cbps(pos, prev, lev, close[t - 1], close[t], cost_cbps)
        adv = low[t] if pos > 0 else (high[t] if pos < 0 else close[t])
        worst_t = bar_net_cbps(pos, prev, lev, close[t - 1], adv, cost_cbps)
        rets.append(net); rets_bps.append(tdiv(net, 100)); sum_r += net
        worst_cbps = min(worst_cbps, worst_t)
        # intrabar trough drawdown, then compound to the close (M6 semantics)
        trough = min(tdiv(equity * max(1, CBPS_PER_X1 + worst_t), CBPS_PER_X1), MAX_EQUITY)
        max_dd_bps = max(max_dd_bps, tdiv((peak - trough) * 10_000, peak))
        equity = min(tdiv(equity * max(1, CBPS_PER_X1 + net), CBPS_PER_X1), MAX_EQUITY)
        peak = max(peak, equity)
        max_dd_bps = max(max_dd_bps, tdiv((peak - equity) * 10_000, peak))
        prev = pos
    net_bps = tdiv((equity - EQUITY_SCALE) * 10_000, EQUITY_SCALE)
    # Sharpe x100 (lib.rs sharpe()): sum_r * isqrt(ppy*1e4) / (n*std), integer
    n_r = len(rets)
    mean = tdiv(sum_r, n_r)
    var = tdiv(sum((r - mean) ** 2 for r in rets), n_r)
    std = isqrt(var)
    sharpe_x100 = tdiv(sum_r * isqrt(ppy * 10_000), n_r * std) if std else 0
    # OOS Sharpe x100 over last 30% (oos_sharpe_from_rets → sharpe_bps, x100 internal)
    split = len(rets_bps) * (OOS_DEN - OOS_NUM) // OOS_DEN
    tail = rets_bps[split:]
    s = sum(r * 100 for r in tail); m = tdiv(s, len(tail))
    v = tdiv(sum((r * 100 - m) ** 2 for r in tail), len(tail)); sd = isqrt(v)
    oos_x100 = tdiv(s * isqrt(ppy * 10_000), len(tail) * sd) if sd else 0
    # CAGR: engine uses Q32 log2/exp2 (agrees with float to a few bps — see lib.rs cagr_bps)
    cagr = ((1 + net_bps / 10_000) ** (ppy / (n_r)) - 1) * 100 if net_bps > -10_000 else float("nan")
    return dict(net_pct=net_bps / 100, maxdd_pct=max_dd_bps / 100,
                worst_pct=tdiv(worst_cbps, 100) / 100, trades=trades, in_mkt=in_mkt,
                sharpe=sharpe_x100 / 100, oos=oos_x100 / 100, cagr_pct=cagr)

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "btc_daily.csv"
    close, low, high = load(path)
    print(f"bars loaded: {len(close)}  (expect 1,096)")
    r = backtest(signals(close), close, low, high)
    committed = dict(sharpe=0.75, oos=1.10, maxdd_pct=16.16, net_pct=47.6,
                     cagr_pct=13.9, worst_pct=-13.54, trades=65, in_mkt=129)
    fmt = {"sharpe": "{:.2f}", "oos": "{:.2f}", "maxdd_pct": "{:.2f}", "net_pct": "{:.1f}",
           "cagr_pct": "{:.1f}", "worst_pct": "{:.2f}", "trades": "{:d}", "in_mkt": "{:d}"}
    label = {"sharpe": "Sharpe", "oos": "OOS Sharpe", "maxdd_pct": "MaxDD %", "net_pct": "Net %",
             "cagr_pct": "CAGR %", "worst_pct": "Worst bar %", "trades": "Trades", "in_mkt": "Bars in mkt"}
    print(f"\n{'metric':<14}{'engine (committed)':>20}{'this script':>16}{'match':>8}")
    print("-" * 58)
    ok = True
    for k in committed:
        a, b = committed[k], r[k]
        s_a, s_b = fmt[k].format(a), fmt[k].format(b)
        m = s_a == s_b
        ok &= m
        print(f"{label[k]:<14}{s_a:>20}{s_b:>16}{'✓' if m else '✗':>8}")
    print("-" * 58)
    print("EVERY COMMITTED NUMBER REPRODUCED INDEPENDENTLY." if ok
          else "MISMATCH — the engine and this script disagree; investigate.")
