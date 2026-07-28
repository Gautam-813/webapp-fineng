# TheFinanceEngine — Impulse Grid EA
### Customer Setup & Activation Guide (v1.10)

Welcome, and thank you for your purchase. This short guide gets your EA installed, licensed, and running. For the full explanation of every setting, see the **Product Manual**.

---

## What you received

- `TheFinanceEngine_ImpulseGrid.ex5` — the ready-to-run Expert Advisor.
- This setup guide and the product manual.

> You do **not** receive source code. The `.ex5` is the compiled, protected program that runs in MetaTrader 5.

---

## Step 1 — Install the EA

1. Open MetaTrader 5.
2. Go to **File → Open Data Folder**.
3. Open **MQL5 → Experts**.
4. Copy `TheFinanceEngine_ImpulseGrid.ex5` into that **Experts** folder.
5. Back in MT5, right-click **Expert Advisors** in the Navigator panel and choose **Refresh**. The EA appears in the list.

## Step 2 — Allow the license server (one-time)

The EA checks your license online, so MT5 must be allowed to reach our server:

1. Go to **Tools → Options → Expert Advisors**.
2. Tick **Allow WebRequest for listed URL**.
3. Add this URL exactly:
   ```
   https://thefinanceengine.com
   ```
   *(If your seller gave you a different server address, use that one instead — it must match the “License server URL” input in Step 4.)*
4. Click **OK**.

## Step 3 — Attach the EA to a chart

1. Open a chart for your symbol (for example **XAUUSD**) and timeframe.
2. Drag **TheFinanceEngine — Impulse Grid** from the Navigator onto the chart.
3. In the dialog, on the **Common** tab, tick **Allow Algo Trading**.

## Step 4 — Enter your license key

In the **Inputs** tab, find the **“0. Licensing”** group at the top:

- **Your license key** — paste the key from your purchase email (format `TFE-XXXX-XXXX-XXXX-XXXX`).
- **License server URL** — leave as provided unless told otherwise.
- **Product code** — leave as `impulse-grid` (do not change).

Click **OK**. Make sure the **Algo Trading** button in the top toolbar is green.

After the server approves the key, the EA remembers it in this MT5 terminal's
`MQL5/Files` folder. On later charts, you may leave **Your license key** empty
and the EA will automatically validate the remembered key. Entering a key in
the Inputs tab always takes priority and replaces the remembered key only after
the server approves it.

## Step 5 — Confirm it activated

- If the license is valid, the EA starts normally and the chart comment clears.
- If something is wrong, the chart shows a message such as *“LICENSE INACTIVE”* with the reason (for example, key missing, expired, or already active on another device). Fix it and re-attach the EA, or press the Algo Trading button off and on.

---

## Moving the EA to another computer or VPS

Each license runs on **one machine at a time**. To move it:

1. Log in to your account at **thefinanceengine.com**.
2. Go to **Account → Licenses**.
3. Find your EA and click **Deregister device**.
4. Install and enter your key on the new machine — it will activate there.

*(Self-service moves are limited per period to prevent sharing. If you hit the limit, it resets on renewal or contact support.)*

## Renewing / topping up

Your license has an expiry date, shown on the **Licenses** page. Before it lapses, use **Top up** on that page to extend it. When a license expires, the EA stops trading until you renew.

---

## Troubleshooting

| Message / symptom | What to do |
|---|---|
| “LICENSE KEY MISSING” | Enter your key in the EA inputs (Step 4). |
| A remembered key is not found | Each MT5 installation has its own `MQL5/Files` folder. Enter the key once in that terminal and let it validate successfully. |
| “Cannot reach license server” + WebRequest note | Add the server URL in Tools → Options → Expert Advisors (Step 2). Check the machine has internet. |
| “active on another device” | Deregister the old device from your dashboard, then re-attach here. |
| “expired” | Top up your subscription on the Licenses page. |
| Algo Trading button is grey | Click it so it turns green; ensure “Allow Algo Trading” was ticked. |

---

## Important notes

- Keep the EA running on a machine with a **stable internet connection** (a VPS is ideal). It re-checks the license periodically; a brief outage is tolerated, but a long one will pause trading.
- **Trading involves substantial risk of loss.** Test on a demo account first and use the EA’s built-in safety limits. Past performance does not guarantee future results.

For help, contact **TheFinanceEngine** through your account dashboard.
