# TheFinanceEngine — Impulse Grid EA
### Product Manual & Setup Guide · Version 1.10

Thank you for choosing **TheFinanceEngine — Impulse Grid**, an automated Expert Advisor for MetaTrader 5 built for gold (XAUUSD) and forex. This manual explains how the EA works, how to install and license it, and what every input does.

> **Important risk notice.** Impulse Grid uses a **grid with martingale-style lot scaling**. With the default multiplier of 2.0, position sizes grow geometrically as a basket builds. This can produce smooth equity curves in ranging conditions and sharp drawdowns in strong adverse trends. Trade on a demo account first, use the built-in safety limits, and never risk capital you cannot afford to lose. Past performance does not guarantee future results.

---

## 1. What the EA does

Impulse Grid trades in three stages:

**1. Signal.** On each new bar it watches a moving-average crossover. In *1-MA mode* it compares price to a single MA; in *2-MA mode* it compares a fast MA to a slow MA. A bullish cross arms a buy; a bearish cross arms a sell.

**2. Confirmed entry.** It does not enter at the crossover. After a signal arms, price must travel a set dollar distance in the signal's direction (the "impulse" confirmation) before the first trade opens. This filters out weak crosses.

**3. Grid & exit.** Once a basket is open, additional trades are added each time price moves a further dollar step from the basket's edge, with each new lot scaled up by a multiplier or a fixed increment. The basket closes when its floating profit reaches your take-profit target — or when any safety limit (global, daily, session, or directional) triggers.

An optional **Counter Grid** ("Both" mode) runs an opposite-direction basket alongside the main one, with its own independent settings.

---

## 2. Requirements

- MetaTrader 5 (latest build recommended)
- A broker account offering XAUUSD or your chosen forex pair
- A VPS or always-on computer is strongly recommended for uninterrupted operation
- Your **license key** (provided at purchase) and an internet connection for activation

---

## 3. Installation

1. In MT5, open **File → Open Data Folder**.
2. Go to **MQL5 → Experts** and copy the `TheFinanceEngine_ImpulseGrid.ex5` file there.
3. Restart MT5 or right-click **Expert Advisors** in the Navigator and choose **Refresh**.
4. Open a chart for your chosen symbol (e.g. XAUUSD) and timeframe.
5. Drag **TheFinanceEngine — Impulse Grid** from the Navigator onto the chart.
6. In the dialog, enable **Allow Algo Trading**, enter your settings, and click **OK**.
7. Make sure the **Algo Trading** button in the top toolbar is green.

You'll see the on-chart dashboard appear (if enabled), showing live trade counts, drawdown, and grid levels.

---

## 4. Licensing & activation

Your purchase includes a license key tied to your account. Activation is automatic on first run when the EA connects to our license server.

- **Single-device binding.** Each key activates on one machine (PC or VPS) at a time.
- **Remembered key.** After a successful server validation, the EA stores the key in this MT5 terminal's `MQL5/Files/TFE_impulse-grid_License.txt`. Later chart attachments may leave the key input empty; the saved key is still validated online before trading is allowed.
- **Moving to a new machine.** Log in to your dashboard at *thefinanceengine.com*, choose the EA, and click **Deregister** to release the current device. The key is then free to activate on your new machine.
- **Keep the EA online.** It needs internet access to validate. On a VPS this is automatic.

*(Detailed dashboard steps are provided separately with your account.)*

---

## 5. Recommended starting settings

**Conservative (suggested for first-time use):**
- Lot Scaling Mode: **Increment** (linear, not martingale), Increment: **0.01**
- Set a **Global Stop-Loss** and a **Daily Loss Cap** to real dollar values — never leave all safety off
- Sessions: **OFF**, Base Lot: **0.01**
- Test on **demo** for at least a few weeks before any live capital

**Standard (as shipped):**
- Lot Scaling Mode: **Multiplier**, factor **2.0** — higher recovery power, higher risk. Understand the drawdown behavior before using.

---

## 6. Full parameter reference

Parameters are grouped in the order they appear in the Inputs tab.

### 1 · Signal / Indicator
| Setting | Default | What it does |
|---|---|---|
| Signal Mode | 1-MA | Chooses the crossover engine: price-vs-MA (1-MA) or fast-MA-vs-slow-MA (2-MA). |
| Fast MA Period | 10 | Fast MA length. **Only used in 2-MA mode.** |
| Main MA Period | 50 | The primary MA — reference for crossovers and MA-touch exits. |
| MA Timeframe | Current | Timeframe the MA is calculated on. |
| MA Method | EMA | Smoothing type: EMA, SMA, SMMA, or LWMA. |
| Applied Price | Close | Price series fed to the MA. |

### 2 · Main Grid: Entry, Lots & Take-Profit
| Setting | Default | What it does |
|---|---|---|
| Basket Mode | Normal | Normal = trend direction only. Both = also runs the Counter Grid. |
| First Entry ($ past signal) | 10.0 | Price must move this many dollars past the crossover before the first trade opens. |
| Grid Step ($ from edge) | 5.0 | Dollar move from the basket's edge before the next grid trade is added. |
| Base Lot | 0.01 | First-trade lot size — **used only when Sessions are OFF** (see §8). |
| Lot Scaling Mode | Multiplier | Multiplier = martingale; Increment = fixed step. Only one applies. |
| Martingale factor | 2.0 | Next lot = last lot × this value (Multiplier mode). |
| Step add | 0.01 | Next lot = last lot + this value (Increment mode). |
| Per-Side Take-Profit ($) | 10.0 | Closes the buy or sell basket when its floating profit (incl. swap) reaches this. |
| Main Magic Number | 888888 | Trade identifier. **Do not set to 0.** |

### 3 · Counter Grid (only if Basket Mode = Both)
A mirror-image basket in the opposite direction, with its own settings. Note the counter **always uses its own Base Lot** regardless of session settings.

| Setting | Default | What it does |
|---|---|---|
| Counter First Entry ($) | 10.0 | Confirmation distance for the first counter trade. |
| Counter Grid Step ($) | 5.0 | Spacing for counter grid additions. |
| Counter Base Lot | 0.01 | First counter-trade lot (not affected by sessions). |
| Counter Lot Scaling Mode | Multiplier | Counter scaling method. |
| Counter martingale factor | 2.0 | Counter multiplier. |
| Counter step add | 0.01 | Counter increment. |
| Counter Per-Side Take-Profit ($) | 10.0 | Counter basket profit target. |
| Counter Magic Number | 888899 | Counter trade identifier. |

### 4 · Global Safety (all trades)
| Setting | Default | What it does |
|---|---|---|
| Global Stop-Loss ($) | 0.0 | Closes **everything** if combined floating loss reaches this. 0 = disabled. |
| Global Take-Profit ($) | 0.0 | Closes **everything** at this combined floating profit. 0 = disabled. |
| Daily Profit Cap ($) | 0.0 | Closes all and stops trading for the rest of the day at this daily profit. 0 = off. |
| Daily Loss Cap ($) | 0.0 | Same, on the loss side. 0 = off. |

> We strongly recommend setting at least a Global Stop-Loss and a Daily Loss Cap.

### 5 · Buy-Side Exit Rules  &nbsp; / &nbsp; 6 · Sell-Side Exit Rules
Independent optional exits for each side. Priority: loss → MA-touch → opposite crossover.

| Setting | Default | What it does |
|---|---|---|
| Enable loss close | false | Turns on the "close side at a set loss" rule. |
| Close at loss ($) | 0.0 | The loss amount that closes the side. **If you enable the rule, set this above 0** — leaving it at 0 closes the side at breakeven. |
| Close on opposite crossover | false | Closes the side when a fresh opposite crossover prints. |
| Close on MA touch | false | Buy: closes if price falls back to the MA. Sell: closes if price rises back to the MA. |

### 7 · Trading Days Filter
Enable to restrict trading to chosen weekdays. When off, the EA trades every day. Defaults: Mon–Fri on, weekends off.

### 8 · Intraday Sessions
Split the day into up to four time windows. **When Sessions are ON, each session's Base Lot sets the first-trade size — this overrides the global Base Lot in §2.** Each session also has an optional floating profit target and loss limit that, when hit, lock that session until the next one.

| Per session | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| Window | 00:00–05:59 | 06:00–11:59 | 12:00–17:59 | 18:00–23:59 |
| Base Lot | 0.01 | 0.05 | 0.08 | 0.09 |

Times use your broker's server time. Overnight windows (start later than end) are supported.

> **Key point:** if you set a Base Lot in §2 but leave Sessions ON, the session Base Lots take over. Turn Sessions OFF to use the single global Base Lot.

### 9 · Dashboard & Export
| Setting | Default | What it does |
|---|---|---|
| Show Dashboard | true | Draggable on-chart panel: trades, buys/sells, worst drawdown, grid-level counts. |
| Export CSV | false | Writes a statistics CSV when the EA is removed from the chart. |

---

## 7. Best-practice checklist

- Run on a **VPS** for 24/5 uptime and stable licensing.
- Always demo-test a new settings set before going live.
- Keep at least one **safety limit** active (Global Stop-Loss and/or Daily Loss Cap).
- Understand that **Multiplier mode is martingale** — size your account and limits accordingly.
- One EA instance per symbol/chart; give each instance a unique Magic Number if you run several.

---

## 8. Support

For setup help, license transfers, or questions, contact **TheFinanceEngine** through your account dashboard.

*This manual describes version 1.10. Trading involves substantial risk of loss and is not suitable for every investor.*
