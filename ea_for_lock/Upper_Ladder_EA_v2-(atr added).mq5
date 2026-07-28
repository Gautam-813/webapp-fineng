//+------------------------------------------------------------------+
//|                                   XAUUSD_Upper_Ladder_EA.mq5     |
//|                        Copyright 2024, MetaTrader 5 Ladder EA    |
//|                                  Copyright 2025, The Finance Engine  |
//|                                             https://www.thefinanceengine.com |
//+------------------------------------------------------------------+
#property copyright "The Finance Engine"
#property link      "https://www.thefinanceengine.com"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//--- Enums
enum ENUM_LOT_MODE
{
   LOT_MULTIPLY,     // Lot Multiplier
   LOT_INCREMENT,    // Lot Increment
   LOT_DECREMENT,    // Lot Decrement
   LOT_FIXED         // Fixed Lot
};

enum ENUM_LADDER_STATE
{
   STATE_INITIAL,    // Waiting for first trade
   STATE_WAIT_SELL,  // Buy placed, waiting for Sell hedge
   STATE_WAIT_BUY    // Sell placed, waiting for next higher Buy
};

//--- Input Parameters
input group "=== Ladder Settings ==="
input double         InpInitialLot = 0.01;               // Initial Lot Size
input double         InpStep = 2.0;                      // Step UP to next Buy ($)
input double         InpGap = 10.0;                      // Gap DOWN to Sell hedge ($)
input bool           InpFlippingMode = true;             // Use Flipping (Close prev on recovery)

input group "=== Lot Progression ==="
input ENUM_LOT_MODE  InpLotMode = LOT_FIXED;             // Lot Calculation Mode
input double         InpLotValue = 0.01;                 // Lot Value (Mult/Inc/Dec/Fixed)

input group "=== Profit Target ==="
input double         InpTotalProfitTarget = 100.0;       // Total Profit Target ($) (0 to disable)
input double         InpStopLoss          = 500.0;       // Net Stop Loss ($) (0 to disable)
input int            InpMaxTrades         = 10;          // Max Open Trades (0 to disable)

input group "=== General Settings ==="
input ulong          InpMagicNumber = 888111;            // Magic Number
input string         InpTradeComment = "UpperLadder";    // Trade Comment
input int            InpSlippage = 30;                   // Slippage (points)

input group "=== TheFinanceEngine License ==="
input bool           InpLicenseEnabled = true;           // Enable license validation
input string         InpLicenseKey = "";                 // License Key (saved after valid check)
input string         InpLicenseServerUrl = "http://127.0.0.1:8000/api/licenses/v1/ea/validate"; // License API URL
input int            InpLicenseCheckHours = 8;           // Re-check Every N Hours
input int            InpLicenseGraceHours = 24;          // Offline Grace After Valid Check

input group "=== ATR Entry Gate ==="
input double          InpATRValue     = 0.0;          // Min ATR Value (0 to disable)
input ENUM_TIMEFRAMES InpATRTimeframe = PERIOD_CURRENT; // ATR Timeframe
input int             InpATRPeriod    = 14;           // ATR Period

input group "=== Trade on Days ==="
input bool InpTradeMonday    = true;   // Trade on Monday
input bool InpTradeTuesday   = true;   // Trade on Tuesday
input bool InpTradeWednesday = true;   // Trade on Wednesday
input bool InpTradeThursday  = true;   // Trade on Thursday
input bool InpTradeFriday    = true;   // Trade on Friday

input group "=== Global Hedge Settings ==="
input double InpHedgeLoss    = 500.0;  // Hedge Loss Limit ($) (0 to disable)

input group "=== Session Trading ==="
input bool   InpUseSessions    = false;    // Use Session Restriction
input bool   InpUseSess1       = true;     // Use Session 1
input string InpSess1Start     = "00:00";  // Sess 1 Start (HH:MM)
input string InpSess1End       = "23:59";  // Sess 1 End (HH:MM)
input bool   InpUseSess2       = false;    // Use Session 2
input string InpSess2Start     = "00:00";  // Sess 2 Start (HH:MM)
input string InpSess2End       = "00:00";  // Sess 2 End (HH:MM)
input bool   InpUseSess3       = false;    // Use Session 3
input string InpSess3Start     = "00:00";  // Sess 3 Start (HH:MM)
input string InpSess3End       = "00:00";  // Sess 3 End (HH:MM)
input bool   InpUseSess4       = false;    // Use Session 4
input string InpSess4Start     = "00:00";  // Sess 4 Start (HH:MM)
input string InpSess4End       = "00:00";  // Sess 4 End (HH:MM)

//--- Global Variables
#define TFE_PRODUCT_CODE "upper_ladder_ea_v2"

CTrade            m_trade;
ENUM_LADDER_STATE g_state = STATE_INITIAL;
double            g_lastBuyPrice = 0;
int               g_tradeCount = 0;
datetime          g_lastActionTime = 0;
bool              g_isHedged = false;      // Flag to track if hedge is active
int               hATR = INVALID_HANDLE;   // ATR Indicator Handle
double            g_accumulatedLoss = 0;   // Realized loss in cycle (for flipping)

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+


input group "=== Daily Profit/Loss Limit ==="
input double InpMaxDailyProfit = 0.0; // Max Daily Profit ($) (0 to disable)
input double InpMaxDailyLoss   = 0.0; // Max Daily Loss ($) (0 to disable)

// --- Daily P/L tracking globals ---
datetime g_TrackingDay     = 0;
bool     g_DailyLimitHit   = false;
bool     g_LicenseValid = false;
datetime g_LastLicenseCheck = 0;
datetime g_LastLicenseSuccess = 0;
string   g_ActiveLicenseKey = "";

//+------------------------------------------------------------------+
//| License Helpers                                                  |
//+------------------------------------------------------------------+
string TrimSpaces(string value)
{
   StringReplace(value, " ", "");
   StringReplace(value, "\t", "");
   StringReplace(value, "\r", "");
   StringReplace(value, "\n", "");
   return value;
}

string LicenseAccountNumber()
{
   return IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
}

string LicenseFileName()
{
   return "TheFinanceEngine\\" + TFE_PRODUCT_CODE + "_" + LicenseAccountNumber() + ".txt";
}

bool ReadSavedLicense(string &licenseKey, datetime &lastValidatedAt)
{
   licenseKey = "";
   lastValidatedAt = 0;

   int handle = FileOpen(LicenseFileName(), FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return false;

   while(!FileIsEnding(handle))
   {
      string line = FileReadString(handle);
      if(StringFind(line, "license_key=") == 0)
         licenseKey = StringSubstr(line, StringLen("license_key="));
      else if(StringFind(line, "last_validated_at=") == 0)
         lastValidatedAt = (datetime)StringToInteger(StringSubstr(line, StringLen("last_validated_at=")));
   }

   FileClose(handle);
   licenseKey = TrimSpaces(licenseKey);
   return (StringLen(licenseKey) > 0);
}

void SaveLicense(string licenseKey)
{
   FolderCreate("TheFinanceEngine");
   int handle = FileOpen(LicenseFileName(), FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("License file save failed. Error: ", GetLastError());
      return;
   }

   FileWrite(handle, "license_key=" + TrimSpaces(licenseKey));
   FileWrite(handle, "product_code=" + TFE_PRODUCT_CODE);
   FileWrite(handle, "mt_account_number=" + LicenseAccountNumber());
   FileWrite(handle, "last_validated_at=" + IntegerToString((long)TimeCurrent()));
   FileClose(handle);
}

string JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return value;
}

bool LicenseResponseAllowed(string response)
{
   return (StringFind(response, "\"allowed\":true") >= 0 || StringFind(response, "\"allowed\": true") >= 0);
}

bool ValidateLicenseWithServer(string licenseKey, string &message)
{
   string payload = "{"
      + "\"license_key\":\"" + JsonEscape(TrimSpaces(licenseKey)) + "\","
      + "\"product_code\":\"" + TFE_PRODUCT_CODE + "\","
      + "\"mt_account_number\":\"" + JsonEscape(LicenseAccountNumber()) + "\","
      + "\"platform\":\"MT5\","
      + "\"client_version\":\"1.00\","
      + "\"broker_server\":\"" + JsonEscape(AccountInfoString(ACCOUNT_SERVER)) + "\""
      + "}";

   char data[];
   int dataSize = StringToCharArray(payload, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(dataSize > 0)
      ArrayResize(data, dataSize - 1);

   char result[];
   string resultHeaders = "";
   string headers = "Content-Type: application/json\r\n";
   ResetLastError();
   int statusCode = WebRequest("POST", InpLicenseServerUrl, headers, 15000, data, result, resultHeaders);
   if(statusCode == -1)
   {
      message = "License server unreachable. WebRequest error: " + IntegerToString(GetLastError());
      return false;
   }

   string response = CharArrayToString(result, 0, -1, CP_UTF8);
   if(statusCode < 200 || statusCode >= 300)
   {
      message = "License server error. HTTP " + IntegerToString(statusCode);
      return false;
   }

   if(LicenseResponseAllowed(response))
   {
      message = "License active";
      return true;
   }

   message = "License blocked: " + response;
   return false;
}

bool EnsureLicenseValid(bool force)
{
   if(!InpLicenseEnabled)
      return true;

   int checkSeconds = (int)MathMax(InpLicenseCheckHours, 1) * 3600;
   if(!force && g_LicenseValid && (TimeCurrent() - g_LastLicenseCheck) < checkSeconds)
      return true;

   string savedKey = "";
   datetime savedLastValidated = 0;
   ReadSavedLicense(savedKey, savedLastValidated);

   string candidateKey = TrimSpaces(InpLicenseKey);
   if(StringLen(candidateKey) == 0)
      candidateKey = savedKey;

   if(StringLen(candidateKey) == 0)
   {
      Comment("License required. Enter your TheFinanceEngine license key in EA inputs.");
      Print("License required. No license key input or saved license file found.");
      return false;
   }

   string message = "";
   bool valid = ValidateLicenseWithServer(candidateKey, message);
   g_LastLicenseCheck = TimeCurrent();

   if(valid)
   {
      g_LicenseValid = true;
      g_LastLicenseSuccess = TimeCurrent();
      g_ActiveLicenseKey = candidateKey;
      SaveLicense(candidateKey);
      Print("License validation passed for account ", LicenseAccountNumber());
      return true;
   }

   int graceSeconds = (int)MathMax(InpLicenseGraceHours, 0) * 3600;
   datetime lastSuccess = (g_LastLicenseSuccess > savedLastValidated ? g_LastLicenseSuccess : savedLastValidated);
   if(lastSuccess > 0 && graceSeconds > 0 && (TimeCurrent() - lastSuccess) <= graceSeconds)
   {
      g_LicenseValid = true;
      Print(message, ". Using offline license grace until next successful check.");
      return true;
   }

   g_LicenseValid = false;
   Comment("License validation failed.\n", message);
   Print(message);
   return false;
}

int OnInit()
{
   if(!EnsureLicenseValid(true))
     {
      Print("License validation failed. EA initialization stopped.");
      return(INIT_FAILED);
     }

   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(InpSlippage);
   
   // DYNAMIC FILLING MODE DETECTION
   SetFillingMode();
   
   m_trade.SetAsyncMode(false);

   UpdateStateFromPositions();

   hATR = iATR(Symbol(), InpATRTimeframe, InpATRPeriod);
   if(hATR == INVALID_HANDLE)
     {
      Print("Failed to create ATR handle");
      return(INIT_FAILED);
     }

   Print("Upper Ladder EA Initialized. Step: ", InpStep, " Gap: ", InpGap);

   // Initialize daily tracking
   MqlDateTime _dt; TimeToStruct(TimeCurrent(), _dt);
   _dt.hour = 0; _dt.min = 0; _dt.sec = 0;
   g_TrackingDay   = StructToTime(_dt);
   g_DailyLimitHit = false;
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Set Dynamic Filling Mode                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
}

void SetFillingMode()
{
   uint filling = (uint)SymbolInfoInteger(Symbol(), SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_FOK) != 0) m_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((filling & SYMBOL_FILLING_IOC) != 0) m_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else m_trade.SetTypeFilling(ORDER_FILLING_RETURN);
}

//+------------------------------------------------------------------+
//| Check if trading is allowed today                               |
//+------------------------------------------------------------------+
bool IsTradeAllowedToday()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   switch(dt.day_of_week)
   {
      case 1: return InpTradeMonday;
      case 2: return InpTradeTuesday;
      case 3: return InpTradeWednesday;
      case 4: return InpTradeThursday;
      case 5: return InpTradeFriday;
      default: return false; // Saturday=6, Sunday=0
   }
}

//+------------------------------------------------------------------+
//| Check and Apply Global Hedge                                     |
//+------------------------------------------------------------------+
void CheckGlobalHedge()
{
   if(InpHedgeLoss <= 0) return; // Feature disabled if 0
   if(g_isHedged) return;

   double buyLots = 0, sellLots = 0, totalProfit = 0;
   int count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) > 0 && PositionGetString(POSITION_SYMBOL) == Symbol() && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         double vol = PositionGetDouble(POSITION_VOLUME);
         if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) buyLots += vol;
         else sellLots += vol;
         
         totalProfit += PositionGetDouble(POSITION_PROFIT);
         count++;
      }
   }

   if(count == 0) return;

   if(totalProfit <= -InpHedgeLoss)
   {
      double net = NormalizeDouble(buyLots - sellLots, 2);
      if(MathAbs(net) < 0.001) { g_isHedged = true; return; }

      ENUM_ORDER_TYPE type = (net > 0) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      double lot = MathAbs(net);
      
      Print("Hedge Triggered! Loss: ", totalProfit, ". Net Exposure: ", net, ". Opening Hedge: ", (type == ORDER_TYPE_BUY ? "BUY " : "SELL "), lot);
      
      double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(Symbol(), SYMBOL_ASK) : SymbolInfoDouble(Symbol(), SYMBOL_BID);
      bool res = (type == ORDER_TYPE_BUY) ? m_trade.Buy(lot, Symbol(), price, 0, 0, "GlobalHedge") : m_trade.Sell(lot, Symbol(), price, 0, 0, "GlobalHedge");
      if(res)
      {
         g_isHedged = true;
      }
   }
}

//+------------------------------------------------------------------+
//| Check if current time is within allowed sessions                 |
//+------------------------------------------------------------------+
bool IsSessionAllowed()
{
   if(!InpUseSessions) return true;
   
   datetime now = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(now, dt);
   int currentMinutes = dt.hour * 60 + dt.min;
   
   bool sess1 = IsInSession(currentMinutes, InpUseSess1, InpSess1Start, InpSess1End);
   bool sess2 = IsInSession(currentMinutes, InpUseSess2, InpSess2Start, InpSess2End);
   bool sess3 = IsInSession(currentMinutes, InpUseSess3, InpSess3Start, InpSess3End);
   bool sess4 = IsInSession(currentMinutes, InpUseSess4, InpSess4Start, InpSess4End);
   
   return (sess1 || sess2 || sess3 || sess4);
}

bool IsInSession(int currentMin, bool use, string start, string end)
{
   if(!use) return false;
   
   string partsStart[];
   string partsEnd[];
   if(StringSplit(start, ':', partsStart) != 2 || StringSplit(end, ':', partsEnd) != 2) return false;
   
   int sMin = (int)StringToInteger(partsStart[0]) * 60 + (int)StringToInteger(partsStart[1]);
   int eMin = (int)StringToInteger(partsEnd[0]) * 60 + (int)StringToInteger(partsEnd[1]);
   
   if(sMin < eMin) return (currentMin >= sMin && currentMin < eMin);
   else return (currentMin >= sMin || currentMin < eMin); // Midnight crossing
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!EnsureLicenseValid(false))
     {
      Print("License validation failed. The EA will remove itself from the chart.");
      ExpertRemove();
      return;
     }

   // Prevent multi-execution
   if(TimeCurrent() == g_lastActionTime) return;

   // 1. Risk Management Check
   if(CheckRiskManagement())
   {
      ResetState();
      return;
   }

   CheckGlobalHedge();
   if(g_isHedged)
   {
      Comment("BASKET HEDGED: Strategy Paused.\nLoss Limit Reached.");
      return;
   }

   double bid = SymbolInfoDouble(Symbol(), SYMBOL_BID);
   double ask = SymbolInfoDouble(Symbol(), SYMBOL_ASK);

   if(!IsTradeAllowedToday() || !IsSessionAllowed())
      Comment("SESSION CLOSED: New Entries Restricted.\nManaging Open Sequence.");

   // 3. Ladder State Machine
   switch(g_state)
   {
      case STATE_INITIAL:
         HandleInitialState(ask);
         break;

      case STATE_WAIT_SELL:
         HandleWaitSell(bid);
         break;

      case STATE_WAIT_BUY:
         HandleWaitBuy(ask);
         break;
   }
}

//+------------------------------------------------------------------+
//| Handle Initial Entry                                             |
//+------------------------------------------------------------------+
void HandleInitialState(double currentAsk)
{
   if(!IsTradeAllowedToday() || !IsSessionAllowed()) return;
   
   if(!CheckATR()) return;

   double lot = CalculateNextLot(g_tradeCount);
   if(m_trade.Buy(lot, Symbol(), currentAsk, 0, 0, InpTradeComment))
   {
      g_lastBuyPrice = currentAsk;
      g_tradeCount++; 
      g_state = STATE_WAIT_SELL;
      g_lastActionTime = TimeCurrent();
      Print("Initial BUY #1 placed @ ", currentAsk, " Lot: ", lot);
   }
}

//+------------------------------------------------------------------+
//| Handle Sequential Sell Hedge                                     |
//+------------------------------------------------------------------+
void HandleWaitSell(double currentBid)
{
   double sellLevel = g_lastBuyPrice - InpGap;

   if(currentBid <= sellLevel && (InpMaxTrades <= 0 || g_tradeCount < InpMaxTrades))
   {
      if(InpFlippingMode)
      {
         g_accumulatedLoss -= GetTotalProfitOnly();
         CloseAll();
      }
      
      double lot = CalculateNextLot(g_tradeCount); 
      if(m_trade.Sell(lot, Symbol(), currentBid, 0, 0, InpTradeComment))
      {
         g_tradeCount++;
         g_state = STATE_WAIT_BUY;
         g_lastActionTime = TimeCurrent();
         if(InpFlippingMode) Print("Flip logic triggered: BUY->SELL. Recorded Loss: ", g_accumulatedLoss);
         else Print("Hedge SELL placed @ ", currentBid, " Lot: ", lot);
      }
   }
}

//+------------------------------------------------------------------+
//| Handle Next Higher Buy                                           |
//+------------------------------------------------------------------+
void HandleWaitBuy(double currentAsk)
{
   double nextBuyLevel = g_lastBuyPrice + InpStep;

   if(currentAsk >= nextBuyLevel && (InpMaxTrades <= 0 || g_tradeCount < InpMaxTrades))
   {
      if(InpFlippingMode)
      {
         g_accumulatedLoss -= GetTotalProfitOnly();
         CloseAll();
      }
      
      double lot = CalculateNextLot(g_tradeCount);
      if(m_trade.Buy(lot, Symbol(), currentAsk, 0, 0, InpTradeComment))
      {
         g_lastBuyPrice = currentAsk;
         g_tradeCount++;
         g_state = STATE_WAIT_SELL;
         g_lastActionTime = TimeCurrent();
         if(InpFlippingMode) Print("Flip logic triggered: SELL->BUY. Recorded Loss: ", g_accumulatedLoss);
         else Print("Next BUY placed @ ", currentAsk, " Lot: ", lot);
      }
   }
}

//+------------------------------------------------------------------+
//| Lot Calculation                                                  |
//+------------------------------------------------------------------+
double CalculateNextLot(int tradeCount)
{
   double lot = InpInitialLot;
   switch(InpLotMode)
   {
      case LOT_MULTIPLY:  lot = InpInitialLot * MathPow(InpLotValue, tradeCount); break;
      case LOT_INCREMENT: lot = InpInitialLot + (InpLotValue * tradeCount); break;
      case LOT_DECREMENT: lot = InpInitialLot - (InpLotValue * tradeCount); break;
      case LOT_FIXED:     lot = InpLotValue; break;
   }
   return NormalizeLot(lot);
}

//+------------------------------------------------------------------+
//| Normalize Lot                                                    |
//+------------------------------------------------------------------+
double NormalizeLot(double lot)
{
   double step = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MAX);
   
   // Senior-level rounding to broker step
   double normalized = MathFloor(lot / step + 0.000001) * step;
   
   if(normalized < minLot) normalized = minLot;
   if(normalized > maxLot) normalized = maxLot;
   
   return NormalizeDouble(normalized, 2);
}

//+------------------------------------------------------------------+
//| Risk Management                                                  |
//+------------------------------------------------------------------+
bool CheckRiskManagement()
{
   double totalProfit = GetTotalProfitOnly();
   double netProfit = totalProfit - g_accumulatedLoss;

   // Profit Target
   if(InpTotalProfitTarget > 0 && netProfit >= (InpTotalProfitTarget - 0.0001))
   {
       Print("Profit Target Reached: $", DoubleToString(netProfit, 2));
       CloseAll();
       return true;
   }

   // Stop Loss
   if(InpStopLoss > 0 && netProfit <= -InpStopLoss)
   {
       Print("Stop Loss Reached: $", DoubleToString(netProfit, 2));
       CloseAll();
       return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Close All Positions                                              |
//+------------------------------------------------------------------+
void CloseAll()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == Symbol() && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         m_trade.PositionClose(ticket);
   }
}

//+------------------------------------------------------------------+
//| Reset State                                                      |
//+------------------------------------------------------------------+
void ResetState()
{
   g_state = STATE_INITIAL;
   g_lastBuyPrice = 0;
   g_tradeCount = 0;
   g_isHedged = false;
   g_accumulatedLoss = 0;
}

double GetTotalProfitOnly()
{
   double profit = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(PositionGetTicket(i) > 0 && PositionGetString(POSITION_SYMBOL) == Symbol() && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) {
         profit += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      }
   }
   return profit;
}

//+------------------------------------------------------------------+
//| Helper function to check ATR gate                               |
//+------------------------------------------------------------------+
bool CheckATR()
{
   if(InpATRValue <= 0) return true;
   
   double atr[1];
   if(CopyBuffer(hATR, 0, 0, 1, atr) > 0)
     {
      if(atr[0] < InpATRValue)
        {
         Comment("WAITING FOR VOLATILITY: ATR (", DoubleToString(atr[0], _Digits), ") < ", DoubleToString(InpATRValue, _Digits));
         return false;
        }
     }
   else return false; // Buffer not ready
   
   return true;
}

//+------------------------------------------------------------------+
//| Update State from Positions (For Restarts)                       |
//+------------------------------------------------------------------+
void UpdateStateFromPositions()
{
   int buys = 0;
   int sells = 0;
   double maxBuyPrice = 0;
   int total = 0;

   for(int i = 0; i < PositionsTotal(); i++)
   {
      if(PositionGetTicket(i) > 0 && PositionGetString(POSITION_SYMBOL) == Symbol() && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         double price = PositionGetDouble(POSITION_PRICE_OPEN);
         total++;
         if(type == POSITION_TYPE_BUY)
         {
            buys++;
            if(price > maxBuyPrice) maxBuyPrice = price;
         }
         else sells++;
      }
   }

   if(buys == 0) g_state = STATE_INITIAL;
   else if(buys > sells)
   {
      g_state = STATE_WAIT_SELL;
      g_lastBuyPrice = maxBuyPrice;
   }
   else
   {
      g_state = STATE_WAIT_BUY;
      g_lastBuyPrice = maxBuyPrice;
   }
   
   g_tradeCount = total;
}

//+------------------------------------------------------------------+
//| Get Last Position Lot (Optional Utility)                         |
//+------------------------------------------------------------------+
double GetLastPositionLot(ENUM_POSITION_TYPE type)
{
   double lastLot = InpInitialLot;
   double maxPrice = 0;
   
   for(int i = 0; i < PositionsTotal(); i++)
   {
      if(PositionGetTicket(i) > 0 && PositionGetString(POSITION_SYMBOL) == Symbol() && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         if(PositionGetInteger(POSITION_TYPE) == type)
         {
            double p = PositionGetDouble(POSITION_PRICE_OPEN);
            if(p > maxPrice) { maxPrice = p; lastLot = PositionGetDouble(POSITION_VOLUME); }
         }
      }
   }
   return lastLot;
}
