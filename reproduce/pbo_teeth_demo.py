#!/usr/bin/env python3
"""
MIZAN — does PBO have teeth? A both-sides demonstration.

MIZAN's composed-PBO flagship credential prints PBO = 0.0759 (not overfit).
A fair reviewer should ask: would that statistic actually CATCH an overfit
search, or does it bless everything? This script answers with the same CSCV
procedure (Bailey, Borwein, Lopez de Prado, Zhu 2017) on two synthetic
search scenarios where the truth is known by construction:

  A. PURE NOISE  — 16 trials of driftless returns. Any "winner" is luck.
                   PBO should be ~0.5 (the winner's OOS rank is a coin flip).
  B. REAL SKILL  — 16 trials, one with genuine drift. The winner is real.
                   PBO should be low.

Method (identical shape to the in-circuit composed PBO, S=16 blocks):
  split the sample into S=16 equal blocks; for each of C(16,8)=12,870
  train/test combinations, pick the best trial by in-sample Sharpe and
  record its RANK out-of-sample. PBO = fraction of combinations where the
  in-sample winner lands in the bottom half out-of-sample.

Run:  python3 pbo_teeth_demo.py     (stdlib only; ~45s, exact — all 12,870)
"""
import itertools, math, random

S, TRIALS, N = 16, 16, 1600           # blocks, trials, bars
random.seed(7)                         # deterministic — same numbers every run

def sharpe(xs):
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / len(xs)
    return m / math.sqrt(v) if v > 0 else 0.0

def pbo(trial_rets):
    """Exact CSCV over all C(S, S/2) splits; returns fraction of splits where
    the in-sample winner ranks in the bottom half out-of-sample."""
    blk = N // S
    blocks = [[t[i * blk:(i + 1) * blk] for i in range(S)] for t in trial_rets]
    bad = total = 0
    for train in itertools.combinations(range(S), S // 2):
        tr = set(train)
        is_sh  = [sharpe([x for b in range(S) if b in tr     for x in blocks[t][b]]) for t in range(TRIALS)]
        oos_sh = [sharpe([x for b in range(S) if b not in tr for x in blocks[t][b]]) for t in range(TRIALS)]
        w = max(range(TRIALS), key=lambda t: is_sh[t])
        rank = sorted(oos_sh).index(oos_sh[w])          # 0 = worst OOS
        bad += rank < TRIALS // 2
        total += 1
    return bad / total

# A · pure noise: 16 driftless trials — the classic overfit search
noise = [[random.gauss(0.0, 0.01) for _ in range(N)] for _ in range(TRIALS)]
# B · real skill: same noise field, but trial 0 carries genuine drift
skill = [list(t) for t in noise]
skill[0] = [x + 0.0012 for x in noise[0]]              # ~1.9 annualized Sharpe

pbo_noise, pbo_skill = pbo(noise), pbo(skill)
print(f"C(16,8) = 12,870 combinations evaluated per scenario (exact, no sampling)\n")
print(f"  A · pure-noise search (winner is luck)   PBO = {pbo_noise:.3f}   → coin flip, no edge"
      f"{'  ✓' if pbo_noise > 0.4 else '  ✗ UNEXPECTED'}")
print(f"  B · genuine-skill search (winner is real) PBO = {pbo_skill:.3f}   → not overfit"
      f"{'  ✓' if pbo_skill < 0.2 else '  ✗ UNEXPECTED'}")
print(f"\n  MIZAN flagship credential (real, in-circuit): PBO = 0.0759 → same regime as B.")
print(f"  The statistic separates luck from skill by construction — it has teeth.")
