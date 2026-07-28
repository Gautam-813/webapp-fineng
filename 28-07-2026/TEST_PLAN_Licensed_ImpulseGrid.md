# Impulse Grid + Licensing — Manual Test Plan
### For Meet & team · run before selling

This verifies the **licensed EA talks to the license server correctly** and enforces every rule. Do these in order. Each test says what to do and what you should see.

---

## A. Preparation

**A0. Run the server locally (or deploy it).**
- Unzip the licensing build, `pip install -r requirements.txt`, `alembic upgrade head`, then `uvicorn app.main:app --reload`.
- Server runs at `http://localhost:8000`. For MT5 to reach `localhost`, run MT5 on the same machine, or deploy the server to Railway/Render and use that public URL.
- **Important:** the server must be reachable over **HTTPS** for a real deployment. MT5 WebRequest works with http for localhost testing but use https in production.

**A1. Compile the EA.**
- Put `TFE_License.mqh` in `MQL5/Include/`.
- Put `TheFinanceEngine_ImpulseGrid.mq5` in `MQL5/Experts/`.
- Open it in MetaEditor and press **Compile**. Expect **0 errors**. (Warnings about unused variables are fine.)
- Confirm `TheFinanceEngine_ImpulseGrid.ex5` is produced. *This `.ex5` is what customers get — never the `.mq5` or `.mqh`.*

**A2. Allow the URL in MT5.**
- Tools → Options → Expert Advisors → tick **Allow WebRequest**, add your server URL (e.g. `http://localhost:8000` for local, or your Railway URL).

**A3. Create a test license (no payment needed).**
- As an admin user, call `POST /api/admin/licenses/issue` with `{ "user_id": <your test user id>, "product_id": <impulse-grid product id>, "duration_days": 30 }`.
- You can use the FastAPI docs UI at `/api/docs` (in debug mode) or `curl`. Copy the returned `license_key`.
- Make sure a **Product** exists with slug `impulse-grid` (the EA's Product code must match a product slug).

---

## B. Core activation tests (on a DEMO account)

**B1. Missing key is blocked.**
- Attach the EA with the License Key field **empty**.
- Expect: chart shows “LICENSE KEY MISSING”, EA does not trade, Experts log prints the same.

**B2. Valid key activates.**
- Set License Key to your test key, correct server URL, product code `impulse-grid`. Attach.
- Expect: chart comment clears, Experts log prints “TFE License: active”. EA begins normal operation.
- On the server, check the `license_activations` table (or the dashboard) — one active device now bound.
- Confirm `MQL5/Files/TFE_impulse-grid_License.txt` was created after the server approved the key.

**B2a. Remembered key activates.**
- Remove and re-attach the EA with the License Key input empty on the same MT5 terminal.
- Expect: Experts log says it is using the remembered key, then prints “TFE License: active”. The EA operates normally.

**B2b. Invalid replacement does not overwrite the remembered key.**
- Enter an invalid key and attach. Expect the invalid key to be denied.
- Re-attach with the License Key input empty.
- Expect: the previously approved remembered key still activates. A rejected manual key must never replace it.

**B3. Wrong product code is rejected.**
- Change Product code to something else (e.g. `wrong-code`) and re-attach.
- Expect: “LICENSE INACTIVE … different product”. No trading.
- Restore it to `impulse-grid` afterward.

**B4. Heartbeat keeps it alive.**
- Leave B2 running. The EA re-checks every 5 minutes (`TFE_HEARTBEAT_SECONDS`).
- On the server, watch `license_validation_logs` — new “allow” rows appear over time. EA keeps trading.

---

## C. Device-binding tests

**C1. Second machine is blocked.**
- With the key active on machine 1, attach the same key on a **second** machine/VPS (or a second MT5 install / different terminal data folder to get a different fingerprint).
- Expect: machine 2 shows “active on another device”, does not trade.

**C2. Deregister then migrate.**
- In the customer dashboard (`/account/licenses`), click **Deregister device**.
- Re-attach on machine 2.
- Expect: machine 2 now activates and trades. Machine 1, on its next heartbeat, will start being denied (it lost the slot).

**C3. Migration cap.**
- Deregister/re-activate repeatedly. After the cap (default 2 per period), the dashboard **Deregister** button should return an error (“Migration limit reached”).
- Confirm a **Top up** resets the counter (C-cap clears after renewal).

---

## D. Subscription / expiry tests

**D1. Expired license stops trading.**
- On the server, set the license `expires_at` to a past date (admin DB edit, or issue with `duration_days` then edit).
- On the EA's next heartbeat (or re-attach), expect: “expired … please top up”, trading stops.

**D2. Top up re-activates.**
- In the dashboard, click **Top up** on that license.
- Re-attach or wait for heartbeat. Expect: EA active again, new expiry date shown.

**D3. Revoke kills it immediately-ish.**
- Call `POST /api/admin/licenses/{id}/set-status` with `{"status":"revoked"}`.
- Next heartbeat/re-attach: “revoked”, trading stops. (Set back to `active` to continue testing.)

---

## E. Resilience tests

**E1. Network blip is tolerated.**
- With the EA active, stop the server (Ctrl-C) briefly, then within the grace window (12h, `TFE_CACHE_GRACE_SECONDS`) let a heartbeat fire.
- Expect: EA keeps trading using the cached “allow” and shows a “using cached license” note — it does **not** halt on a short outage.

**E2. Long outage eventually stops it.**
- (Optional / config-dependent.) If the server stays unreachable beyond the grace window, the next heartbeat denies and trading pauses. Verify the message is clear.

**E3. URL not allowed.**
- Remove the URL from Tools → Options → WebRequest and re-attach.
- Expect: “Cannot reach license server … allow the URL” message. This confirms the guidance is correct for customers.

---

## F. Trading-behavior regression (make sure licensing didn't change trading)

**F1. Same behavior as the un-licensed build.**
- On a demo/backtest, compare the licensed EA (with a valid key) against your previously-validated rebranded build over the same period/settings.
- Expect: **identical trades**. The licensing code only gates whether `OnTick` runs; it does not touch entry/grid/exit math. Any difference means something's wrong — report it.

> Note: the Strategy Tester does **not** run WebRequest. This is **already handled**: the licensing client detects tester/optimizer mode (`MQL_TESTER` / `MQL_OPTIMIZATION`) and bypasses the online check, so backtests run your trading logic normally. Live and demo real-time runs still enforce licensing. So F1 works as written — just run a normal backtest.

---

## G. Packaging check (what customers receive)

**G1. Only the `.ex5` ships.**
- Confirm the customer download contains **only** `TheFinanceEngine_ImpulseGrid.ex5` + the customer README + product manual.
- Confirm **no** `.mq5` and **no** `.mqh` are included anywhere in the customer package.

**G2. Fresh-machine install.**
- On a clean MT5, follow the customer README start to finish. It should activate with only the `.ex5` and the key. If any step is unclear, note it and I'll fix the README.

---

## Pass criteria

All of B, C, D, and E1/E3 pass, and F1 shows identical trading. If any fail, send me the exact chart message + the matching row from `license_validation_logs` and I'll diagnose.

---

## Solved: backtesting with licensing

The licensing client auto-detects the Strategy Tester and optimizer and bypasses the online check there, so you can backtest and optimize normally. Real-time (live/demo) runs enforce licensing. Nothing extra to do.
