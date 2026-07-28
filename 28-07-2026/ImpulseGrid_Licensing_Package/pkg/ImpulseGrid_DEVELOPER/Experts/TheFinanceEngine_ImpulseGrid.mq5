//+------------------------------------------------------------------+
//|                        TheFinanceEngine_ImpulseGrid.mq5          |
//|                     Copyright 2026, TheFinanceEngine. All rights. |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, TheFinanceEngine"
#property link      "https://thefinanceengine.com"
#property version   "1.10"
#property strict
   
#include <Trade\Trade.mqh>
#include <TFE_License.mqh>   // TheFinanceEngine online licensing

//--- Input Parameters
enum ENUM_ENTRY_MODE
  {
   ENTRY_1_MA=0, // 1 MA Crossover (Price vs MA)
   ENTRY_2_MA=1  // 2 MA Crossover (Fast MA vs Slow MA)
  };

enum ENUM_LOT_MODE
  {
   LOT_MODE_MULTIPLIER=0, // Lot Multiplier (Martingale)
   LOT_MODE_INCREMENT=1  // Lot Increment (Step)
  };

enum ENUM_ORDER_MODE
  {
   ORDER_MODE_NORMAL=0, // Normal (Trend Only)
   ORDER_MODE_BOTH=1    // Both Orders (Trend + Counter)
  };

input group             "===== 0. Licensing (TheFinanceEngine) ====="
input string            InpLicenseKey    = "";                         // Your license key (TFE-XXXX-XXXX-XXXX-XXXX)
input string            InpLicenseServer = "https://thefinanceengine.com"; // License server URL
input string            InpProductCode   = "impulse-grid";             // Product code (do not change)

input group             "===== 1. Signal / Indicator ====="
input ENUM_ENTRY_MODE   InpEntryMode         = ENTRY_1_MA;  // Signal Mode: 1-MA (price x MA) or 2-MA (fast x slow)
input int               InpFastMAPeriod      = 10;          // Fast MA Period (used ONLY in 2-MA mode)
input int               InpMAPeriod          = 50;          // Main MA Period (the crossover / MA-touch line)
input ENUM_TIMEFRAMES   InpMATimeframe       = PERIOD_CURRENT; // MA Timeframe
input ENUM_MA_METHOD    InpMAMethod          = MODE_EMA;    // MA Method (EMA / SMA / SMMA / LWMA)
input ENUM_APPLIED_PRICE InpAppliedPrice     = PRICE_CLOSE; // Applied Price for the MA

input group             "===== 2. Main Grid: Entry, Lots & Take-Profit ====="
input ENUM_ORDER_MODE   InpOrderMode            = ORDER_MODE_NORMAL; // Basket Mode: Normal (trend only) or Both (adds counter)
input double            InpAllTradeStartDistUSD = 10.0;     // First Entry: $ price must move PAST signal before entry
input double            InpAllTradeGridStepUSD  = 5.0;      // Grid Step: $ move from basket edge before adding next trade
input double            InpInitialLot           = 0.01;     // Base Lot (used ONLY when Sessions are OFF)
input ENUM_LOT_MODE     InpLotMode              = LOT_MODE_MULTIPLIER; // Lot Scaling Mode: Multiplier (martingale) or Increment (step)
input double            InpLotMultiplier        = 2.0;      // -- Martingale factor: nextLot = lastLot x this (Multiplier mode)
input double            InpLotIncrement         = 0.01;     // -- Step add: nextLot = lastLot + this (Increment mode)
input double            InpMainBasketProfitUSD  = 10.0;     // Per-Side Take-Profit ($ floating, incl. swap) - closes that side
input int               InpMagicNumber          = 888888;   // Main Magic Number (do NOT set 0)

input group             "===== 3. Counter Grid (only if Basket Mode = Both) ====="
input double            InpCounterStartDistUSD  = 10.0;     // Counter First Entry: $ move past signal before counter entry
input double            InpCounterGridStepUSD   = 5.0;      // Counter Grid Step ($ from counter basket edge)
input double            InpCounterInitialLot    = 0.01;     // Counter Base Lot (always used; sessions do NOT override this)
input ENUM_LOT_MODE     InpCounterLotMode       = LOT_MODE_MULTIPLIER; // Counter Lot Scaling Mode (Multiplier / Increment)
input double            InpCounterLotMultiplier = 2.0;      // -- Counter martingale factor (Multiplier mode)
input double            InpCounterLotIncrement  = 0.01;     // -- Counter step add (Increment mode)
input double            InpCounterBasketProfitUSD = 10.0;   // Counter Per-Side Take-Profit ($)
input int               InpCounterMagicNumber   = 888899;   // Counter Magic Number

input group             "===== 4. Global Safety (all trades) ====="
input double            InpBasketLoss           = 0.0;      // Global Stop-Loss ($ across ALL trades; 0 = disabled)
input double            InpBasketProfit         = 0.0;      // Global Take-Profit ($ across ALL trades; 0 = disabled)
input double            InpMaxDailyProfit       = 0.0;      // Daily Profit Cap ($; closes all & stops for the day; 0 = off)
input double            InpMaxDailyLoss         = 0.0;      // Daily Loss Cap ($; closes all & stops for the day; 0 = off)

input group             "===== 5. Buy-Side Exit Rules ====="
input bool              InpDirBuyEnableLossClose          = false; // Enable: close BUY side at a set loss (needs $ below)
input double            InpDirBuyLossAmountUSD            = 0.0;   // Close BUY side when its loss reaches this $ (set > 0 if enabled!)
input bool              InpDirBuyCloseOnOppositeCrossover = false; // Close BUY side on a fresh bearish crossover
input bool              InpDirBuyCloseOnMATouch           = false; // Close BUY side when price falls back to the MA

input group             "===== 6. Sell-Side Exit Rules ====="
input bool              InpDirSellEnableLossClose          = false; // Enable: close SELL side at a set loss (needs $ below)
input double            InpDirSellLossAmountUSD            = 0.0;   // Close SELL side when its loss reaches this $ (set > 0 if enabled!)
input bool              InpDirSellCloseOnOppositeCrossover = false; // Close SELL side on a fresh bullish crossover
input bool              InpDirSellCloseOnMATouch           = false; // Close SELL side when price rises back to the MA

input group             "===== 7. Trading Days Filter ====="
input bool              InpUseTradingDays  = false;         // Enable Trading-Days Filter (else trades every day)
input bool              InpTradeMonday     = true;          // Trade on Monday?
input bool              InpTradeTuesday    = true;          // Trade on Tuesday?
input bool              InpTradeWednesday  = true;          // Trade on Wednesday?
input bool              InpTradeThursday   = true;          // Trade on Thursday?
input bool              InpTradeFriday     = true;          // Trade on Friday?
input bool              InpTradeSaturday   = false;         // Trade on Saturday?
input bool              InpTradeSunday     = false;         // Trade on Sunday?

input group             "===== 8. Intraday Sessions ====="
input bool              InpUseSessionControl = true;        // Use Sessions (ON = session Base Lot overrides global Base Lot)

input group "Session 1 Setting"
input bool              InpEnableSession1    = true;        // Enable Session 1?
input string            InpSession1Start     = "00:00";     // Session 1 Start (HH:MM)
input string            InpSession1End       = "05:59";     // Session 1 End (HH:MM)
input double            InpSession1Profit    = 0.0;         // Session 1 Profit Target ($ floating; locks session when hit)
input double            InpSession1Loss      = 0.0;         // Session 1 Loss Limit ($ floating; locks session when hit)
input double            InpSession1StartLot  = 0.01;        // Session 1 Base Lot (first-trade lot in this window)

input group "Session 2 Setting"
input bool              InpEnableSession2    = true;        // Enable Session 2?
input string            InpSession2Start     = "06:00";     // Session 2 Start (HH:MM)
input string            InpSession2End       = "11:59";     // Session 2 End (HH:MM)
input double            InpSession2Profit    = 0.0;         // Session 2 Profit Target ($ floating; locks session when hit)
input double            InpSession2Loss      = 0.0;         // Session 2 Loss Limit ($ floating; locks session when hit)
input double            InpSession2StartLot  = 0.05;        // Session 2 Base Lot (first-trade lot in this window)

input group "Session 3 Setting"
input bool              InpEnableSession3    = true;        // Enable Session 3?
input string            InpSession3Start     = "12:00";     // Session 3 Start (HH:MM)
input string            InpSession3End       = "17:59";     // Session 3 End (HH:MM)
input double            InpSession3Profit    = 0.0;         // Session 3 Profit Target ($ floating; locks session when hit)
input double            InpSession3Loss      = 0.0;         // Session 3 Loss Limit ($ floating; locks session when hit)
input double            InpSession3StartLot  = 0.08;        // Session 3 Base Lot (first-trade lot in this window)

input group "Session 4 Setting"
input bool              InpEnableSession4    = true;        // Enable Session 4?
input string            InpSession4Start     = "18:00";     // Session 4 Start (HH:MM)
input string            InpSession4End       = "23:59";     // Session 4 End (HH:MM)
input double            InpSession4Profit    = 0.0;         // Session 4 Profit Target ($ floating; locks session when hit)
input double            InpSession4Loss      = 0.0;         // Session 4 Loss Limit ($ floating; locks session when hit)
input double            InpSession4StartLot  = 0.09;        // Session 4 Base Lot (first-trade lot in this window)

input group             "===== 9. Dashboard & Export ====="
input bool              InpShowDashboard      = true;       // Show on-chart Dashboard
input bool              InpSaveDataCSV        = false;      // Export stats to CSV when EA is removed

//--- Global Variables
CTrade         trade;
int            handleMA;
int            handleFastMA;
double         bufferMA[];
double         bufferFastMA[];

// Signal Tracking
bool           buySignalActive = false;
bool           sellSignalActive = false;
bool           counterBuySignalActive = false;
bool           counterSellSignalActive = false;
double         buyRefPrice = 0;
double         sellRefPrice = 0;
double         counterBuyRefPrice = 0;
double         counterSellRefPrice = 0;

// To prevent double opening on same tick
datetime       lastBuyTime = 0;
datetime       lastSellTime = 0;
datetime       lastCounterBuyTime = 0;
datetime       lastCounterSellTime = 0;

// Session Tracking
int            activeSessionIndex = -1;
bool           currentSessionLocked = false;
datetime       lastSessionAnchor = 0;

// Daily Tracking
datetime       currentTradeDay = 0;
bool           dailyLimitReached = false;

// --- Dashboard Tracking ---
int            totalTrades = 0;
int            totalBuy = 0;
int            totalSell = 0;
int            totalSwings = 0;
double         highestDDRecorded = 0; // Persistent record of worst DD
datetime       highestDDTime = 0;    // Time when record was set
int            maxTradeLevels[11]; // 0=1, 1=2 ... 9=10, 10=11+

// UI Positioning & State
int            dashX = 20;
int            dashY = 70;
bool           isDragging = false;
int            dragOffsetX = 0, dragOffsetY = 0;
string         dashPrefix = "TFE_ImpulseGrid_";

// Closure State Flags (to prevent multi-counting)
bool           isClosingBuy = false;
bool           isClosingSell = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // --- TheFinanceEngine licensing gate ---
   if(!TFE_LicenseInit(InpLicenseKey, InpLicenseServer, InpProductCode))
      return(INIT_FAILED);

   handleMA = iMA(_Symbol, InpMATimeframe, InpMAPeriod, 0, InpMAMethod, InpAppliedPrice);
   if(handleMA == INVALID_HANDLE) return(INIT_FAILED);
   
   if(InpEntryMode == ENTRY_2_MA)
   {
      handleFastMA = iMA(_Symbol, InpMATimeframe, InpFastMAPeriod, 0, InpMAMethod, InpAppliedPrice);
      if(handleFastMA == INVALID_HANDLE) return(INIT_FAILED);
   }
   
   ArraySetAsSeries(bufferMA, true);
   ArraySetAsSeries(bufferFastMA, true);
   trade.SetExpertMagicNumber(InpMagicNumber);
   
   // --- Dynamic Filling Mode Detection ---
   uint fillingMode = (uint)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((fillingMode & SYMBOL_FILLING_IOC) != 0) trade.SetTypeFilling(ORDER_FILLING_IOC);
   else if((fillingMode & SYMBOL_FILLING_FOK) != 0) trade.SetTypeFilling(ORDER_FILLING_FOK);
   else trade.SetTypeFilling(ORDER_FILLING_RETURN);
   
   // --- Dashboard Init ---
   if(InpShowDashboard)
   {
      ChartSetInteger(0, CHART_EVENT_MOUSE_MOVE, true);
      CreateDashboard();
      UpdateDashboard();
   }
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(InpShowDashboard) DeleteDashboard();
   if(InpSaveDataCSV) ExportDashboardToCSV();
}

//+------------------------------------------------------------------+
//| Get Daily Closed Profit                                          |
//+------------------------------------------------------------------+
double GetDailyClosedProfit()
{
   datetime now = TimeCurrent();
   datetime startOfDay = now - (now % 86400); // Start of the current day
   
   HistorySelect(startOfDay, now);
   
   double dailyProfit = 0.0;
   
   for(int i = 0; i < HistoryDealsTotal(); i++)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket > 0)
      {
         long magic = HistoryDealGetInteger(ticket, DEAL_MAGIC);
         if(magic == InpMagicNumber || magic == InpCounterMagicNumber || InpMagicNumber == 0)
         {
            long entry = HistoryDealGetInteger(ticket, DEAL_ENTRY);
            if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_INOUT)
            {
               dailyProfit += HistoryDealGetDouble(ticket, DEAL_PROFIT) + 
                              HistoryDealGetDouble(ticket, DEAL_COMMISSION) + 
                              HistoryDealGetDouble(ticket, DEAL_SWAP);
            }
         }
      }
   }
   return dailyProfit;
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // --- TheFinanceEngine licensing guard (blocks trading if inactive) ---
   if(!TFE_LicenseOK()) return;

   // Handle Closure State Resets
   if(isClosingBuy && CountPositions(POSITION_TYPE_BUY) == 0) isClosingBuy = false;
   if(isClosingSell && CountPositions(POSITION_TYPE_SELL) == 0) isClosingSell = false;

   // Update Drawdown tracking (Permanent Record)
   double floating = CalculateProfit(POSITION_TYPE_BUY) + CalculateProfit(POSITION_TYPE_SELL) +
                     CalculateProfit(POSITION_TYPE_BUY, InpCounterMagicNumber) + CalculateProfit(POSITION_TYPE_SELL, InpCounterMagicNumber);
   if(PositionsTotal() > 0 && floating < 0)
   {
      if(floating < highestDDRecorded) 
      {
         highestDDRecorded = floating;
         highestDDTime = TimeCurrent();
      }
   }
   if(InpShowDashboard) UpdateDashboard();

   if(CopyBuffer(handleMA, 0, 0, 3, bufferMA) < 3) return;
   if(InpEntryMode == ENTRY_2_MA && CopyBuffer(handleFastMA, 0, 0, 3, bufferFastMA) < 3) return;

   // 0a. Update Daily Lock Status & Check Limits
   datetime now = TimeCurrent();
   datetime today = now - (now % 86400); 
   if(today != currentTradeDay)
   {
      currentTradeDay = today;
      dailyLimitReached = false;
   }

   if(dailyLimitReached) return;

   double openProfit = CalculateProfit(POSITION_TYPE_BUY) + CalculateProfit(POSITION_TYPE_SELL) +
                       CalculateProfit(POSITION_TYPE_BUY, InpCounterMagicNumber) + CalculateProfit(POSITION_TYPE_SELL, InpCounterMagicNumber);
   double closedProfit = GetDailyClosedProfit();
   double totalDailyProfit = openProfit + closedProfit;

   if((InpMaxDailyProfit > 0 && totalDailyProfit >= InpMaxDailyProfit) ||
      (InpMaxDailyLoss > 0 && totalDailyProfit <= -InpMaxDailyLoss))
   {
      // Only set dailyLimitReached if ALL trades are successfully closed
      int buyRemaining = CloseAll(POSITION_TYPE_BUY, "daily_limit");
      int sellRemaining = CloseAll(POSITION_TYPE_SELL, "daily_limit");
      int cBuyRemaining = CloseAll(POSITION_TYPE_BUY, "daily_limit", InpCounterMagicNumber);
      int cSellRemaining = CloseAll(POSITION_TYPE_SELL, "daily_limit", InpCounterMagicNumber);
      
      if(buyRemaining == 0 && sellRemaining == 0 && cBuyRemaining == 0 && cSellRemaining == 0)
      {
         buySignalActive = false;
         sellSignalActive = false;
         counterBuySignalActive = false;
         counterSellSignalActive = false;
         dailyLimitReached = true;
         Print("Daily Limit Reached and all trades closed. Total Day Profit: ", totalDailyProfit);
      }
      return; // Stop processing further ticks today
   }

   // 0. Update Session State
   UpdateSessionState();

   // 1. Detect Crossovers (On New Bar)
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   
   if(currentBarTime != lastBarTime)
   {
      double close1 = iClose(_Symbol, _Period, 1);
      double close2 = iClose(_Symbol, _Period, 2);
      double ma1    = bufferMA[1];
      double ma2    = bufferMA[2];
      
      bool isBullishCrossover = false;
      bool isBearishCrossover = false;

      if(InpEntryMode == ENTRY_1_MA)
      {
         isBullishCrossover = (close1 > ma1 && close2 <= ma2);
         isBearishCrossover = (close1 < ma1 && close2 >= ma2);
      }
      else if(InpEntryMode == ENTRY_2_MA)
      {
         double fastMA1 = bufferFastMA[1];
         double fastMA2 = bufferFastMA[2];
         isBullishCrossover = (fastMA1 > ma1 && fastMA2 <= ma2);
         isBearishCrossover = (fastMA1 < ma1 && fastMA2 >= ma2);
      }

      // Bullish Crossover
      if(isBullishCrossover)
      {
         buySignalActive = true;
         buyRefPrice = close1;
         
         if(InpOrderMode == ORDER_MODE_BOTH)
         {
            counterSellSignalActive = true;
            counterSellRefPrice = close1;
         }
      }
      
      // Bearish Crossover
      if(isBearishCrossover)
      {
         sellSignalActive = true;
         sellRefPrice = close1;
         
         if(InpOrderMode == ORDER_MODE_BOTH)
         {
            counterBuySignalActive = true;
            counterBuyRefPrice = close1;
         }
      }
      
      lastBarTime = currentBarTime;
   }

   // 2. Manage Basket and Session Exits
   ManageBasketExits();
   ManageDirectionalExitRules();

   // 3. Manage Grid (Entry)
   ManageGrid();
}

//+------------------------------------------------------------------+
//| Manage Grid Entry Logic                                          |
//+------------------------------------------------------------------+
void ManageGrid()
{
   // Check if today is an allowed trading day
   if(!IsTradeDay()) return;

   // Check if we are in a valid session
   if(InpUseSessionControl)
   {
      if(activeSessionIndex < 0) return;
      if(currentSessionLocked) return;
   }

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   datetime now = TimeCurrent();

   // --- BUY GRID MANAGEMENT ---
   if(isClosingBuy) return; // Don't add to grid while closing
   
   int buyCount = CountPositions(POSITION_TYPE_BUY);
   if(buyCount == 0 && buySignalActive)
   {
      if(ask >= buyRefPrice + InpAllTradeStartDistUSD)
      {
         double lot = GetSessionStartLot();
         if(OpenTrade(POSITION_TYPE_BUY, lot, "Start_Buy_Impulse"))
         {
            buySignalActive = false;
            lastBuyTime = now;
         }
      }
   }
   else if(buyCount > 0 && now > lastBuyTime)
   {
      double highPrice, lowPrice, lastLot;
      GetGridExtremes(POSITION_TYPE_BUY, highPrice, lowPrice, lastLot);
      
      if(ask >= highPrice + InpAllTradeGridStepUSD || ask <= lowPrice - InpAllTradeGridStepUSD)
      {
         double nextLot = (InpLotMode == LOT_MODE_MULTIPLIER) ? lastLot * InpLotMultiplier : lastLot + InpLotIncrement;
         if(OpenTrade(POSITION_TYPE_BUY, nextLot, "Grid_Buy_Add"))
            lastBuyTime = now;
      }
   }

   // --- SELL GRID MANAGEMENT ---
   if(isClosingSell) return; // Don't add to grid while closing

   int sellCount = CountPositions(POSITION_TYPE_SELL);
   if(sellCount == 0 && sellSignalActive)
   {
      if(bid <= sellRefPrice - InpAllTradeStartDistUSD)
      {
         double lot = GetSessionStartLot();
         if(OpenTrade(POSITION_TYPE_SELL, lot, "Start_Sell_Impulse"))
         {
            sellSignalActive = false;
            lastSellTime = now;
         }
      }
   }
   else if(sellCount > 0 && now > lastSellTime)
   {
      double highPrice, lowPrice, lastLot;
      GetGridExtremes(POSITION_TYPE_SELL, highPrice, lowPrice, lastLot);
      
      if(bid <= lowPrice - InpAllTradeGridStepUSD || bid >= highPrice + InpAllTradeGridStepUSD)
      {
         double nextLot = (InpLotMode == LOT_MODE_MULTIPLIER) ? lastLot * InpLotMultiplier : lastLot + InpLotIncrement;
         if(OpenTrade(POSITION_TYPE_SELL, nextLot, "Grid_Sell_Add"))
            lastSellTime = now;
      }
   }

   // --- COUNTER GRID MANAGEMENT (BOTH MODE) ---
   if(InpOrderMode == ORDER_MODE_BOTH)
   {
      // Counter Buy Logic
      int cBuyCount = CountPositions(POSITION_TYPE_BUY, InpCounterMagicNumber);
      if(cBuyCount == 0 && counterBuySignalActive)
      {
         if(bid <= counterBuyRefPrice - InpCounterStartDistUSD)
         {
            double lot = InpCounterInitialLot;
            if(OpenTrade(POSITION_TYPE_BUY, lot, "Start_Counter_Buy", InpCounterMagicNumber))
            {
               counterBuySignalActive = false;
               lastCounterBuyTime = now;
            }
         }
      }
      else if(cBuyCount > 0 && now > lastCounterBuyTime)
      {
         double highPrice, lowPrice, lastLot;
         GetGridExtremes(POSITION_TYPE_BUY, highPrice, lowPrice, lastLot, InpCounterMagicNumber);
         
         if(ask >= highPrice + InpCounterGridStepUSD || ask <= lowPrice - InpCounterGridStepUSD)
         {
            double nextLot = (InpCounterLotMode == LOT_MODE_MULTIPLIER) ? lastLot * InpCounterLotMultiplier : lastLot + InpCounterLotIncrement;
            if(OpenTrade(POSITION_TYPE_BUY, nextLot, "Grid_Counter_Buy", InpCounterMagicNumber))
               lastCounterBuyTime = now;
         }
      }

      // Counter Sell Logic
      int cSellCount = CountPositions(POSITION_TYPE_SELL, InpCounterMagicNumber);
      if(cSellCount == 0 && counterSellSignalActive)
      {
         if(ask >= counterSellRefPrice + InpCounterStartDistUSD)
         {
            double lot = InpCounterInitialLot;
            if(OpenTrade(POSITION_TYPE_SELL, lot, "Start_Counter_Sell", InpCounterMagicNumber))
            {
               counterSellSignalActive = false;
               lastCounterSellTime = now;
            }
         }
      }
      else if(cSellCount > 0 && now > lastCounterSellTime)
      {
         double highPrice, lowPrice, lastLot;
         GetGridExtremes(POSITION_TYPE_SELL, highPrice, lowPrice, lastLot, InpCounterMagicNumber);
         
         if(bid <= lowPrice - InpCounterGridStepUSD || bid >= highPrice + InpCounterGridStepUSD)
         {
            double nextLot = (InpCounterLotMode == LOT_MODE_MULTIPLIER) ? lastLot * InpCounterLotMultiplier : lastLot + InpCounterLotIncrement;
            if(OpenTrade(POSITION_TYPE_SELL, nextLot, "Grid_Counter_Sell", InpCounterMagicNumber))
               lastCounterSellTime = now;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Manage Basket & Session Profit/Loss Exits                        |
//+------------------------------------------------------------------+
void ManageBasketExits()
{
   double totalBuyProfit = CalculateProfit(POSITION_TYPE_BUY);
   double totalSellProfit = CalculateProfit(POSITION_TYPE_SELL);
   double globalProfit = totalBuyProfit + totalSellProfit;
   
   double cTotalBuyProfit = CalculateProfit(POSITION_TYPE_BUY, InpCounterMagicNumber);
   double cTotalSellProfit = CalculateProfit(POSITION_TYPE_SELL, InpCounterMagicNumber);
   double cGlobalProfit = cTotalBuyProfit + cTotalSellProfit;

   // 1. Main Basket Profit (Per Side)
   if(totalBuyProfit >= InpMainBasketProfitUSD && (CountPositions(POSITION_TYPE_BUY) > 0)) 
   {
      CloseAll(POSITION_TYPE_BUY, "basket_profit");
      buySignalActive = false;
   }
   if(totalSellProfit >= InpMainBasketProfitUSD && (CountPositions(POSITION_TYPE_SELL) > 0))
   {
      CloseAll(POSITION_TYPE_SELL, "basket_profit");
      sellSignalActive = false;
   }
   
   // 1a. Global Basket Profit (Counter)
   if(InpOrderMode == ORDER_MODE_BOTH)
   {
      if(cTotalBuyProfit >= InpCounterBasketProfitUSD && cTotalBuyProfit != 0)
      {
         if(CloseAll(POSITION_TYPE_BUY, "counter_basket_profit", InpCounterMagicNumber) == 0) counterBuySignalActive = false;
      }
      if(cTotalSellProfit >= InpCounterBasketProfitUSD && cTotalSellProfit != 0)
      {
         if(CloseAll(POSITION_TYPE_SELL, "counter_basket_profit", InpCounterMagicNumber) == 0) counterSellSignalActive = false;
      }
   }

   // 1b. Global Basket Profit (All Positions)
   if(InpBasketProfit > 0 && (globalProfit + cGlobalProfit) >= InpBasketProfit)
   {
      CloseAll(POSITION_TYPE_BUY, "global_basket_tp");
      CloseAll(POSITION_TYPE_SELL, "global_basket_tp");
      buySignalActive = false;
      sellSignalActive = false;
      
      if(InpOrderMode == ORDER_MODE_BOTH)
      {
         CloseAll(POSITION_TYPE_BUY, "global_basket_tp", InpCounterMagicNumber);
         CloseAll(POSITION_TYPE_SELL, "global_basket_tp", InpCounterMagicNumber);
         counterBuySignalActive = false;
         counterSellSignalActive = false;
      }
   }

   // 2. Global Basket Loss (All Positions)
   if(InpBasketLoss > 0 && (globalProfit + cGlobalProfit) <= -InpBasketLoss)
   {
      CloseAll(POSITION_TYPE_BUY, "basket_loss");
      CloseAll(POSITION_TYPE_SELL, "basket_loss");
      buySignalActive = false;
      sellSignalActive = false;
      
      if(InpOrderMode == ORDER_MODE_BOTH)
      {
         CloseAll(POSITION_TYPE_BUY, "basket_loss", InpCounterMagicNumber);
         CloseAll(POSITION_TYPE_SELL, "basket_loss", InpCounterMagicNumber);
         counterBuySignalActive = false;
         counterSellSignalActive = false;
      }
   }

   // 3. Session Statistics
   if(InpUseSessionControl && activeSessionIndex >= 0 && !currentSessionLocked)
   {
      double sProfit, sLoss;
      GetSessionProfitSettings(activeSessionIndex, sProfit, sLoss);
      
      if(sProfit > 0 && (globalProfit + cGlobalProfit) >= sProfit)
      {
         int bRem = CloseAll(POSITION_TYPE_BUY, "session_tp");
         int sRem = CloseAll(POSITION_TYPE_SELL, "session_tp");
         int cbRem = CloseAll(POSITION_TYPE_BUY, "session_tp", InpCounterMagicNumber);
         int csRem = CloseAll(POSITION_TYPE_SELL, "session_tp", InpCounterMagicNumber);
         if(bRem == 0 && sRem == 0 && cbRem == 0 && csRem == 0)
            currentSessionLocked = true;
      }
      else if(sLoss > 0 && (globalProfit + cGlobalProfit) <= -sLoss)
      {
         int bRem = CloseAll(POSITION_TYPE_BUY, "session_sl");
         int sRem = CloseAll(POSITION_TYPE_SELL, "session_sl");
         int cbRem = CloseAll(POSITION_TYPE_BUY, "session_sl", InpCounterMagicNumber);
         int csRem = CloseAll(POSITION_TYPE_SELL, "session_sl", InpCounterMagicNumber);
         if(bRem == 0 && sRem == 0 && cbRem == 0 && csRem == 0)
            currentSessionLocked = true;
      }
   }
}

//+------------------------------------------------------------------+
//| Manage Directional Exit Rules (MA Touch, Opposite X, Loss)       |
//+------------------------------------------------------------------+
void ManageDirectionalExitRules()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double maVal = bufferMA[0];
   
   // --- Buy Directional Exits ---
   int buyCountMain = CountPositions(POSITION_TYPE_BUY, InpMagicNumber);
   int buyCountCounter = CountPositions(POSITION_TYPE_BUY, InpCounterMagicNumber);
   
   if(buyCountMain > 0 || buyCountCounter > 0)
   {
      double p = CalculateProfit(POSITION_TYPE_BUY, InpMagicNumber) + CalculateProfit(POSITION_TYPE_BUY, InpCounterMagicNumber);
      bool close = false;
      string reason = "";
      
      if(InpDirBuyEnableLossClose && p <= -InpDirBuyLossAmountUSD) { close = true; reason = "dir_buy_loss"; }
      else if(InpDirBuyCloseOnMATouch && bid <= maVal) { close = true; reason = "dir_buy_ma_touch"; }
      else if(InpDirBuyCloseOnOppositeCrossover)
      {
         // We check if a Bearish crossover just happened in the current bar
         bool oppCrossover = false;
         if(InpEntryMode == ENTRY_1_MA)
            oppCrossover = (iClose(_Symbol, _Period, 1) < bufferMA[1] && iClose(_Symbol, _Period, 2) >= bufferMA[2]);
         else if(InpEntryMode == ENTRY_2_MA)
            oppCrossover = (bufferFastMA[1] < bufferMA[1] && bufferFastMA[2] >= bufferMA[2]);

         if(oppCrossover)
         { close = true; reason = "dir_buy_opp_x"; }
      }
      
      if(close) 
      {
         CloseAll(POSITION_TYPE_BUY, reason, InpMagicNumber);
         CloseAll(POSITION_TYPE_BUY, reason, InpCounterMagicNumber);
         buySignalActive = false;
         counterBuySignalActive = false;
      }
   }

   // --- Sell Directional Exits ---
   int sellCountMain = CountPositions(POSITION_TYPE_SELL, InpMagicNumber);
   int sellCountCounter = CountPositions(POSITION_TYPE_SELL, InpCounterMagicNumber);
   
   if(sellCountMain > 0 || sellCountCounter > 0)
   {
      double p = CalculateProfit(POSITION_TYPE_SELL, InpMagicNumber) + CalculateProfit(POSITION_TYPE_SELL, InpCounterMagicNumber);
      bool close = false;
      string reason = "";
      
      if(InpDirSellEnableLossClose && p <= -InpDirSellLossAmountUSD) { close = true; reason = "dir_sell_loss"; }
      else if(InpDirSellCloseOnMATouch && ask >= maVal) { close = true; reason = "dir_sell_ma_touch"; }
      else if(InpDirSellCloseOnOppositeCrossover)
      {
         bool oppCrossover = false;
         if(InpEntryMode == ENTRY_1_MA)
            oppCrossover = (iClose(_Symbol, _Period, 1) > bufferMA[1] && iClose(_Symbol, _Period, 2) <= bufferMA[2]);
         else if(InpEntryMode == ENTRY_2_MA)
            oppCrossover = (bufferFastMA[1] > bufferMA[1] && bufferFastMA[2] <= bufferMA[2]);

         if(oppCrossover) 
         { close = true; reason = "dir_sell_opp_x"; }
      }
      
      if(close) 
      {
         CloseAll(POSITION_TYPE_SELL, reason, InpMagicNumber);
         CloseAll(POSITION_TYPE_SELL, reason, InpCounterMagicNumber);
         sellSignalActive = false;
         counterSellSignalActive = false;
      }
   }
}

//+------------------------------------------------------------------+
//| Session Management Functions                                     |
//+------------------------------------------------------------------+
void UpdateSessionState()
{
   if(!InpUseSessionControl)
   {
      activeSessionIndex = 0;
      return;
   }

   datetime now = TimeCurrent();
   datetime anchor = now - (now % 86400); // Start of day
   
   if(anchor != lastSessionAnchor)
   {
      lastSessionAnchor = anchor;
      currentSessionLocked = false; // Reset lock on new day
   }

   int curMin = GetMinuteOfDay(now);
   int detected = -1;

   for(int i=0; i<4; i++)
   {
      bool enabled; string start, end; double p, l, lot;
      GetSessionConfig(i, enabled, start, end, p, l, lot);
      if(!enabled) continue;
      
      int sMin = ParseTimeToMinutes(start);
      int eMin = ParseTimeToMinutes(end);
      
      if(IsTimeInSession(curMin, sMin, eMin))
      {
         detected = i;
         break;
      }
   }

   if(detected != activeSessionIndex)
   {
      activeSessionIndex = detected;
      currentSessionLocked = false; // Reset lock when entering a NEW session
      if(activeSessionIndex >= 0) Print("Entered Session ", activeSessionIndex + 1);
   }
}

void GetSessionConfig(int idx, bool &en, string &s, string &e, double &p, double &l, double &lot)
{
   if(idx==0) { en=InpEnableSession1; s=InpSession1Start; e=InpSession1End; p=InpSession1Profit; l=InpSession1Loss; lot=InpSession1StartLot; }
   else if(idx==1) { en=InpEnableSession2; s=InpSession2Start; e=InpSession2End; p=InpSession2Profit; l=InpSession2Loss; lot=InpSession2StartLot; }
   else if(idx==2) { en=InpEnableSession3; s=InpSession3Start; e=InpSession3End; p=InpSession3Profit; l=InpSession3Loss; lot=InpSession3StartLot; }
   else { en=InpEnableSession4; s=InpSession4Start; e=InpSession4End; p=InpSession4Profit; l=InpSession4Loss; lot=InpSession4StartLot; }
}

void GetSessionProfitSettings(int idx, double &p, double &l)
{
   bool en; string s, e; double lot;
   GetSessionConfig(idx, en, s, e, p, l, lot);
}

double GetSessionStartLot()
{
   if(!InpUseSessionControl || activeSessionIndex < 0) return InpInitialLot;
   bool en; string s, e; double p, l, lot;
   GetSessionConfig(activeSessionIndex, en, s, e, p, l, lot);
   return lot;
}

int GetMinuteOfDay(datetime t) { MqlDateTime dt; TimeToStruct(t, dt); return dt.hour * 60 + dt.min; }

bool IsTradeDay()
{
   if(!InpUseTradingDays) return true;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   switch(dt.day_of_week)
   {
      case 0: return InpTradeSunday;
      case 1: return InpTradeMonday;
      case 2: return InpTradeTuesday;
      case 3: return InpTradeWednesday;
      case 4: return InpTradeThursday;
      case 5: return InpTradeFriday;
      case 6: return InpTradeSaturday;
      default: return false;
   }
}

int ParseTimeToMinutes(string t)
{
   string parts[];
   if(StringSplit(t, ':', parts) != 2) return 0;
   return (int)StringToInteger(parts[0]) * 60 + (int)StringToInteger(parts[1]);
}

bool IsTimeInSession(int cur, int start, int end)
{
   if(start < end) return (cur >= start && cur <= end);
   return (cur >= start || cur <= end); // Overnight support
}

//+------------------------------------------------------------------+
//| Core Trade Helpers                                               |
//+------------------------------------------------------------------+
bool OpenTrade(long type, double lot, string comment, int magic = -1)
{
   int m = (magic == -1) ? InpMagicNumber : magic;
   trade.SetExpertMagicNumber(m);
   
   bool res = false;
   double price = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(type == POSITION_TYPE_BUY) res = trade.Buy(NormalizeLot(lot), _Symbol, price, 0, 0, comment);
   else res = trade.Sell(NormalizeLot(lot), _Symbol, price, 0, 0, comment);
   
   if(!res) Print("Trade Error: ", GetLastError());
   else 
   {
      totalTrades++;
      if(type == POSITION_TYPE_BUY) totalBuy++;
      else totalSell++;
   }
   
   trade.SetExpertMagicNumber(InpMagicNumber); // Reset to default
   return res;
}

int CloseAll(long type, string reason, int magic = -1)
{
   int m = (magic == -1) ? InpMagicNumber : magic;
   // Check if trading is allowed to avoid "Market Closed" errors spamming the log
   if((ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE) == SYMBOL_TRADE_MODE_DISABLED) return CountPositions(type, m);

   // Throttling: Only attempt to send close orders once per second per type and magic
   // We skip throttling for counter magic to avoid complexity with static vars, 
   // or just use basic generic throttling.
   static datetime lastCloseBuy = 0;
   static datetime lastCloseSell = 0;
   datetime now = TimeCurrent();
   
   if(m == InpMagicNumber)
   {
      if(type == POSITION_TYPE_BUY) { if(now - lastCloseBuy < 1) return CountPositions(type, m); lastCloseBuy = now; }
      if(type == POSITION_TYPE_SELL) { if(now - lastCloseSell < 1) return CountPositions(type, m); lastCloseSell = now; }
   }

   int count = CountPositions(type, m);
   if(count > 0 && m == InpMagicNumber)
   {
      if(type == POSITION_TYPE_BUY) isClosingBuy = true;
      else isClosingSell = true;

      totalSwings++;
      if(count >= 11) maxTradeLevels[10]++;
      else maxTradeLevels[count-1]++;
   }

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == m && PositionGetInteger(POSITION_TYPE) == type)
      {
         ClosePositionWithComment(ticket, reason, m);
      }
   }
   
   return CountPositions(type, m);
}

bool ClosePositionWithComment(ulong ticket, string closeComment, int magic = -1)
{
   int m = (magic == -1) ? InpMagicNumber : magic;
   if(!PositionSelectByTicket(ticket)) return false;
   MqlTradeRequest req; MqlTradeResult res; ZeroMemory(req); ZeroMemory(res);
   req.action = TRADE_ACTION_DEAL; req.position = ticket; req.symbol = _Symbol;
   req.volume = PositionGetDouble(POSITION_VOLUME); req.magic = m; req.comment = closeComment;
   if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) { req.type = ORDER_TYPE_SELL; req.price = SymbolInfoDouble(_Symbol, SYMBOL_BID); }
   else { req.type = ORDER_TYPE_BUY; req.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK); }
   uint f = (uint)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((f & SYMBOL_FILLING_IOC) != 0) req.type_filling = ORDER_FILLING_IOC;
   else if((f & SYMBOL_FILLING_FOK) != 0) req.type_filling = ORDER_FILLING_FOK;
   else req.type_filling = ORDER_FILLING_RETURN;
   return OrderSend(req, res);
}

int CountPositions(long type, int magic = -1)
{
   int m = (magic == -1) ? InpMagicNumber : magic;
   int c = 0;
   for(int i=0; i<PositionsTotal(); i++) {
      if(PositionGetTicket(i)>0 && PositionGetInteger(POSITION_MAGIC)==m && PositionGetInteger(POSITION_TYPE)==type) c++;
   }
   return c;
}

double CalculateProfit(long type, int magic = -1)
{
   int m = (magic == -1) ? InpMagicNumber : magic;
   double p = 0;
   for(int i=0; i<PositionsTotal(); i++) {
      if(PositionGetTicket(i)>0 && PositionGetInteger(POSITION_MAGIC)==m && PositionGetInteger(POSITION_TYPE)==type)
         p += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP) ;
   }
   return p;
}

void GetGridExtremes(long type, double &hi, double &lo, double &lot, int magic = -1)
{
   int m = (magic == -1) ? InpMagicNumber : magic;
   hi = -1; lo = 1e10; lot = 0;
   for(int i=0; i<PositionsTotal(); i++) {
      if(PositionGetTicket(i)>0 && PositionGetInteger(POSITION_MAGIC)==m && PositionGetInteger(POSITION_TYPE)==type) {
         double pr = PositionGetDouble(POSITION_PRICE_OPEN);
         if(pr > hi) hi = pr; if(pr < lo) lo = pr; lot = PositionGetDouble(POSITION_VOLUME);
      }
   }
}

double NormalizeLot(double lot)
{
   double s = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double m = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double x = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   
   // Find the normalized lot based on volume step
   double n = MathRound(lot/s)*s;
   
   // If we are in grid/multiplier mode, ensure the lot actually increases 
   // (Important for low lots like 0.01 with low multipliers)
   // We only do this if the original lot was > 0, implying it's a grid addition.
   
   double res = MathMin(x, MathMax(m, n));
   return NormalizeDouble(res, 2);
}

//+------------------------------------------------------------------+
//| Dashboard UI Creation                                            |
//+------------------------------------------------------------------+
void CreateDashboard()
{
   DeleteDashboard(); // Clean start
   
   int w = 260;
   int h = 330; // Adjusted height for grouping
   
   // Background & Header
   CreateRect("BG", dashX, dashY, w, h, C'20,20,30', C'50,50,60');
   CreateRect("Header", dashX, dashY, w, 28, C'40,70,110', C'60,90,130');
   
   // Title
   CreateLabel("Title", dashX + 10, dashY + 5, "⚡ TheFinanceEngine — Impulse Grid", 10, "Trebuchet MS", clrWhite);
   
   // -- Section 1: Trade Stats --
   CreateLabel("TotalTrade", dashX + 10, dashY + 40,  "Total Trades: 0", 9, "Trebuchet MS", clrGold);
   CreateLabel("TotalBuy",   dashX + 15, dashY + 55,  "  - Buy: 0", 8, "Consolas", clrSkyBlue);
   CreateLabel("TotalSell",  dashX + 15, dashY + 70,  "  - Sell: 0", 8, "Consolas", clrTomato);
   
   CreateLabel("TotalSwing", dashX + 10, dashY + 85,  "Total Swings: 0", 9, "Trebuchet MS", clrGold);
   
   // Divider 1
   CreateLine("Div1", dashX + 10, dashY + 105, w - 20, clrGray);
   
   // -- Section 2: Drawdown --
   CreateLabel("MaxDD", dashX + 10, dashY + 115, "Highest DD Recorded: $0.00", 9, "Trebuchet MS", clrYellow);
   
   // Divider 2
   CreateLine("Div2", dashX + 10, dashY + 140, w - 20, clrGray);
   
   // -- Section 3: Level Distribution --
   CreateLabel("MLTitle", dashX + 10, dashY + 150, "Max Trade Level Breakdown", 9, "Trebuchet MS", clrWhite);
   
   string levels[] = {"10+", "10", "9", "8", "7", "6", "5", "4", "3", "2", "1"};
   for(int i=0; i<11; i++)
   {
      CreateLabel("ML_"+IntegerToString(i), dashX + 15, dashY + 175 + (i*13), levels[i] + ":- 0", 8, "Consolas");
   }
}

void UpdateDashboard()
{
   if(ObjectFind(0, dashPrefix + "BG") < 0) CreateDashboard();

   // -- Update Positions (for dragging) --
   ObjectSetInteger(0, dashPrefix + "BG", OBJPROP_XDISTANCE, dashX);
   ObjectSetInteger(0, dashPrefix + "BG", OBJPROP_YDISTANCE, dashY);
   
   ObjectSetInteger(0, dashPrefix + "Header", OBJPROP_XDISTANCE, dashX);
   ObjectSetInteger(0, dashPrefix + "Header", OBJPROP_YDISTANCE, dashY);
   
   ObjectSetInteger(0, dashPrefix + "Title", OBJPROP_XDISTANCE, dashX + 10);
   ObjectSetInteger(0, dashPrefix + "Title", OBJPROP_YDISTANCE, dashY + 5);
   
   SetLabelText("TotalTrade", "Total Trades: " + IntegerToString(totalTrades));
   SetLabelPos("TotalTrade", dashX + 10, dashY + 40);
   
   SetLabelText("TotalBuy", "  - Buy: " + IntegerToString(totalBuy));
   SetLabelPos("TotalBuy", dashX + 15, dashY + 55);
   
   SetLabelText("TotalSell", "  - Sell: " + IntegerToString(totalSell));
   SetLabelPos("TotalSell", dashX + 15, dashY + 70);
   
   SetLabelText("TotalSwing", "Total Swings: " + IntegerToString(totalSwings));
   SetLabelPos("TotalSwing", dashX + 10, dashY + 85);
   
   // Divider 1
   SetRectPos("Div1", dashX + 10, dashY + 105);
   
   string ddStr = "Max DD: " + DoubleToString(highestDDRecorded, 2);
   if(highestDDTime > 0) ddStr += " [" + TimeToString(highestDDTime, TIME_DATE|TIME_MINUTES) + "]";
   
   SetLabelText("MaxDD", ddStr);
   SetLabelPos("MaxDD", dashX + 10, dashY + 115);
   
   // Divider 2
   SetRectPos("Div2", dashX + 10, dashY + 140);
   
   SetLabelPos("MLTitle", dashX + 10, dashY + 150);
   
   for(int i=0; i<11; i++)
   {
      string lbl = (i == 0) ? "10+" : IntegerToString(11-i);
      int val = maxTradeLevels[10-i];
      SetLabelText("ML_"+IntegerToString(i), lbl + ":- " + IntegerToString(val));
      SetLabelPos("ML_"+IntegerToString(i), dashX + 15, dashY + 170 + (i*13));
   }
   
   ChartRedraw();
}

void CreateRect(string name, int x, int y, int w, int h, color bg, color border)
{
   string n = dashPrefix + name;
   ObjectCreate(0, n, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, n, OBJPROP_COLOR, border);
   ObjectSetInteger(0, n, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_BACK, false);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
}

void CreateLine(string name, int x, int y, int w, color clr)
{
   CreateRect(name, x, y, w, 1, clr, clr);
}

void SetRectPos(string name, int x, int y) { ObjectSetInteger(0, dashPrefix + name, OBJPROP_XDISTANCE, x); ObjectSetInteger(0, dashPrefix + name, OBJPROP_YDISTANCE, y); }

void CreateLabel(string name, int x, int y, string txt, int size, string font="Trebuchet MS", color clr=clrWhite)
{
   string n = dashPrefix + name;
   ObjectCreate(0, n, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, n, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, size);
   ObjectSetString(0, n, OBJPROP_FONT, font);
   ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_BACK, false);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
}

void SetLabelText(string name, string txt) { ObjectSetString(0, dashPrefix + name, OBJPROP_TEXT, txt); }
void SetLabelPos(string name, int x, int y) { ObjectSetInteger(0, dashPrefix + name, OBJPROP_XDISTANCE, x); ObjectSetInteger(0, dashPrefix + name, OBJPROP_YDISTANCE, y); }

void DeleteDashboard()
{
   ObjectsDeleteAll(0, dashPrefix);
   ChartRedraw();
}

//+------------------------------------------------------------------+
//| Chart Event Handler (For Dragging)                               |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(!InpShowDashboard) return;

   if(id == CHARTEVENT_MOUSE_MOVE)
   {
      int x = (int)lparam;
      int y = (int)dparam;
      uint mouse_state = (uint)StringToInteger(sparam);
      
      if((mouse_state & 1) == 1) // Left click held
      {
         if(!isDragging)
         {
            // Check if mouse is within BG bounds (dragging by background OR header)
            int bgX = (int)ObjectGetInteger(0, dashPrefix + "BG", OBJPROP_XDISTANCE);
            int bgY = (int)ObjectGetInteger(0, dashPrefix + "BG", OBJPROP_YDISTANCE);
            int bgW = (int)ObjectGetInteger(0, dashPrefix + "BG", OBJPROP_XSIZE);
            int bgH = (int)ObjectGetInteger(0, dashPrefix + "BG", OBJPROP_YSIZE);
            
            if(x >= bgX && x <= bgX + bgW && y >= bgY && y <= bgY + bgH)
            {
               isDragging = true;
               dragOffsetX = x - bgX;
               dragOffsetY = y - bgY;
            }
         }
         
         if(isDragging)
         {
            dashX = x - dragOffsetX;
            dashY = y - dragOffsetY;
            UpdateDashboard();
         }
      }
      else isDragging = false;
   }
}

//+------------------------------------------------------------------+
//| Export Dashboard Metrics to CSV                                  |
//+------------------------------------------------------------------+
void ExportDashboardToCSV()
{
   string fileName = "TFE_ImpulseGrid_Stats_" + _Symbol + ".csv";
   int handle = FileOpen(fileName, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle, "Metric", "Value");
      FileWrite(handle, "Symbol", _Symbol);
      FileWrite(handle, "Total Trades", totalTrades);
      FileWrite(handle, "Total Buy", totalBuy);
      FileWrite(handle, "Total Sell", totalSell);
      FileWrite(handle, "Total Swings", totalSwings);
      FileWrite(handle, "Highest Drawdown", DoubleToString(highestDDRecorded, 2));
      FileWrite(handle, "Highest DD Time", TimeToString(highestDDTime));
      
      FileWrite(handle, "--- Level Breakdown ---", "");
      for(int i = 0; i < 11; i++)
      {
         string lbl = (i == 0) ? "Level 10+" : "Level " + IntegerToString(11 - i);
         FileWrite(handle, lbl, maxTradeLevels[10 - i]);
      }
      
      FileClose(handle);
      Print("Dashboard data successfully exported to: MQL5/Files/", fileName);
   }
   else
   {
      Print("Failed to open CSV file for writing! Error: ", GetLastError());
   }
}
