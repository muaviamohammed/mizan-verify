# MIZAN — verify a trading backtest without ever seeing the strategy

**Prove a backtest is real without revealing the strategy.** MIZAN is a zero-knowledge
proving system for systematic finance: it turns a trading track record into a
cryptographic credential — proof that the performance is real, *after costs, no
lookahead, out-of-sample, and deflated for how many strategies were tried* — while the
strategy, its parameters, and its data stay private.

This repository is the **public, zero-trust verification side**. You do not need MIZAN's
servers, or MIZAN's word, to check a credential. Everything here re-derives the numbers
locally, on your machine.

> **Prove the edge. Never reveal the strategy.**

- Live engine & registry: **https://mizan.market**
- Working paper (SSRN): **[Who Counts the Trials? A Committed Trial Ledger for Enforcing the Deflated Sharpe Ratio in Zero-Knowledge](https://ssrn.com/abstract=7187038)**
- The refusal story, with downloadable proofs: **https://mizan.market/research/the-gate-refused-its-maker**

---

## What problem this solves

Every anti-overfitting statistic in quantitative finance — the **Deflated Sharpe Ratio**,
the **Probability of Backtest Overfitting**, **Hansen's Superior Predictive Ability** test —
is parameterized by the size of the search that produced the result: *how many strategies
did you try before this one worked?* That number is normally **self-reported by the party
being judged**. Understate it, and the correction for luck evaporates. A thousand honest
backtests with only the best one published is a lie that contains no lookahead anywhere in
it, and no property of a single backtest can detect how many siblings it had.

MIZAN closes that hole. The trial set is **committed to a Merkle tree** before evaluation,
so the trial count *N* is the **leaf count of the tree**, not a reported scalar; the winner
is forced, inside a zero-knowledge proof (a STARK), to be the **maximum of the committed
trials**; and the deflation is recomputed **in-circuit** on Merkle-pinned prices, after a
cost floor that cannot be softened. The correction can no longer be understated by the
person it judges. To our knowledge this is the first engine to enforce **both canonical
schools of backtest honesty** — the López de Prado / Bailey deflation program and the
White / Hansen multiple-testing program — inside a zero-knowledge proof, in production.

## Reproduce a live credential yourself (no MIZAN binary required)

`reproduce/` re-implements the in-circuit backtest in **~200 lines of dependency-free
Python** — no numpy, no pandas, so every line is auditable. It reads the pinned public
data and reproduces a live credential's committed numbers **to the printed digit**
(integer-faithful arithmetic — equality, not tolerance).

```bash
cd reproduce
python3 mizan_recompute.py btc_daily.csv
```

Expected: every committed metric (Sharpe, out-of-sample Sharpe, max drawdown, net return,
worst bar) reproduced independently, matching the credential exactly.

The overfitting test reproduces too — the exact combinatorially-symmetric cross-validation
(CSCV) over all **C(16,8) = 12,870** splits. Run it against constructed scenarios where the
truth is known and watch pure noise get flagged while genuine skill clears, so you can
confirm the test has teeth before trusting any verdict it emits:

```bash
python3 pbo_teeth_demo.py
```

## Independent verification of a full credential

A MIZAN credential is a real RISC Zero STARK. The era-pinned verifier re-checks a credential
bundle against **your own copy** of the public data, trusting no one — 17 independent checks
(guest image id, zk receipt, data-root binding, gate policy, annualization basis, cost floor,
and the verdict itself), returning non-zero on anything dishonest. Every credential names the
exact engine era that judged it and verifies against that era forever. Download bundles and
verifier builds from **https://mizan.market/verify**.

## Who this is for

- **Quants** with a real edge who can't afford to reveal it — prove performance without
  disclosing the strategy or the model.
- **Allocators** tired of taking track records on faith — verify any credential offline,
  trusting no one, including MIZAN.
- **Researchers** in quantitative finance and cryptography — the anti-overfitting framework
  of Bailey, López de Prado, Hansen, and Harvey, enforced inside STARKs (RISC Zero zkVM).

## Honest boundaries

A credential is a **backtest seal — history made honest, not a forecast.** It says nothing
about future returns, and it does not model fills or capacity beyond a committed cost floor.
**High-frequency and fill-dependent strategies are refused permanently**, because bar data
cannot honestly establish counterfactual fills. MIZAN's own flagship credential is ruled
**not statistically significant** (Deflated Sharpe 0.68) and is published that way — a
verifier that fails its own author, in public, is the only kind worth trusting.

## Keywords

zero-knowledge deflated Sharpe ratio · committed trial ledger · STARK backtest verification ·
prove a backtest without revealing the strategy · verify a track record without trusting the
manager · backtest overfitting proof · probability of backtest overfitting · cryptographic
backtest honesty · verifiable AI for finance · systematic trading · RISC Zero · quantitative
finance · López de Prado · Deflated Sharpe Ratio · Superior Predictive Ability

---

*Mizan Verification, Inc. — MIT-licensed verification tooling. The proving engine and its
guest circuits are not part of this repository; verification never requires them.*
