//+------------------------------------------------------------------+
//|                                       TFE_License.mqh             |
//|                     Copyright 2026, TheFinanceEngine              |
//|   Reusable online-licensing client for TheFinanceEngine EAs.     |
//|                                                                  |
//|   Usage in an EA:                                                |
//|     #include <TFE_License.mqh>                                   |
//|     input string InpLicenseKey = "";                             |
//|     input string InpLicenseServer = "https://your-domain";       |
//|     input string InpProductCode = "impulse-grid";                |
//|     // in OnInit():  if(!TFE_LicenseInit(...)) return INIT_FAILED;|
//|     // in OnTick():  if(!TFE_LicenseOK()) return;                 |
//+------------------------------------------------------------------+
#property strict

// ---- Configuration defaults (overridable by the EA) ----
#define TFE_HEARTBEAT_SECONDS      300     // re-validate every 5 min
#define TFE_CACHE_GRACE_SECONDS    43200   // trust last "allow" for 12h on network error
#define TFE_HTTP_TIMEOUT_MS        5000

// ---- Internal state ----
string   _tfe_key         = "";
string   _tfe_server      = "";
string   _tfe_product     = "";
bool     _tfe_allowed     = false;         // last known decision
datetime _tfe_last_ok     = 0;             // last successful "allow" (server-confirmed)
datetime _tfe_last_check  = 0;             // last time we called the server
string   _tfe_last_msg    = "";
string   _tfe_fingerprint = "";
string   _tfe_key_file    = "";
bool     _tfe_key_loaded  = false;

//+------------------------------------------------------------------+
//| Return a product-specific key file in this terminal's Files dir. |
//| Example: MQL5/Files/TFE_impulse-grid_License.txt                 |
//+------------------------------------------------------------------+
string _tfe_license_file(const string product)
{
   string safe = product;
   if(safe == "") safe = "default";
   StringReplace(safe, "\\", "_");
   StringReplace(safe, "/", "_");
   StringReplace(safe, ":", "_");
   StringReplace(safe, "*", "_");
   StringReplace(safe, "?", "_");
   StringReplace(safe, "\"", "_");
   StringReplace(safe, "<", "_");
   StringReplace(safe, ">", "_");
   StringReplace(safe, "|", "_");
   return "TFE_" + safe + "_License.txt";
}

//+------------------------------------------------------------------+
//| Read a remembered key from MQL5/Files.                           |
//+------------------------------------------------------------------+
string _tfe_load_key()
{
   if(_tfe_key_file == "") return "";

   int handle = FileOpen(_tfe_key_file, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE) return "";

   string saved = FileReadString(handle);
   FileClose(handle);
   StringTrimLeft(saved);
   StringTrimRight(saved);
   return saved;
}

//+------------------------------------------------------------------+
//| Remember a server-approved key in MQL5/Files.                    |
//+------------------------------------------------------------------+
bool _tfe_save_key(const string key)
{
   if(_tfe_key_file == "" || key == "") return false;

   int handle = FileOpen(_tfe_key_file, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("TFE License: could not save remembered key (error ", GetLastError(), ").");
      return false;
   }

   FileWriteString(handle, key);
   FileFlush(handle);
   FileClose(handle);
   return true;
}

//+------------------------------------------------------------------+
//| Build a stable-enough machine fingerprint (sandbox-limited).     |
//| Combines terminal path, CPU/RAM/OS, account login + broker.      |
//+------------------------------------------------------------------+
string TFE_Fingerprint()
{
   if(_tfe_fingerprint != "") return _tfe_fingerprint;

   string raw = "";
   raw += TerminalInfoString(TERMINAL_PATH);
   raw += "|" + (string)TerminalInfoInteger(TERMINAL_CPU_CORES);
   raw += "|" + (string)TerminalInfoInteger(TERMINAL_MEMORY_PHYSICAL);
   raw += "|" + TerminalInfoString(TERMINAL_OS_VERSION);
   raw += "|" + (string)AccountInfoInteger(ACCOUNT_LOGIN);
   raw += "|" + AccountInfoString(ACCOUNT_SERVER);

   // Simple, dependency-free hash (djb2) -> hex string.
   ulong h = 5381;
   for(int i = 0; i < StringLen(raw); i++)
      h = ((h << 5) + h) + (ulong)StringGetCharacter(raw, i);
   _tfe_fingerprint = StringFormat("%016I64X", h);
   return _tfe_fingerprint;
}

//+------------------------------------------------------------------+
//| Minimal JSON string-field extractor (no external libs).          |
//+------------------------------------------------------------------+
string _tfe_json_str(const string js, const string field)
{
   string pat = "\"" + field + "\"";
   int p = StringFind(js, pat);
   if(p < 0) return "";
   p = StringFind(js, ":", p);
   if(p < 0) return "";
   // skip spaces / opening quote
   int n = StringLen(js);
   p++;
   while(p < n && (StringGetCharacter(js, p) == ' ' || StringGetCharacter(js, p) == '\"')) p++;
   int start = p;
   while(p < n)
   {
      ushort c = StringGetCharacter(js, p);
      if(c == '\"' || c == ',' || c == '}') break;
      p++;
   }
   return StringSubstr(js, start, p - start);
}

//+------------------------------------------------------------------+
//| Call the server /api/license/validate. Returns true on allow.    |
//| On network failure, falls back to cache grace window.            |
//+------------------------------------------------------------------+
bool _tfe_call_server()
{
   string url = _tfe_server + "/api/license/validate";
   string body = StringFormat(
      "{\"license_key\":\"%s\",\"fingerprint\":\"%s\",\"product_code\":\"%s\",\"account_login\":\"%I64d\"}",
      _tfe_key, TFE_Fingerprint(), _tfe_product, AccountInfoInteger(ACCOUNT_LOGIN));

   char post[]; char result[]; string headers = "Content-Type: application/json\r\n";
   int len = StringToCharArray(body, post, 0, StringLen(body), CP_UTF8);
   if(len > 0) ArrayResize(post, len);   // drop trailing null so body length is exact

   ResetLastError();
   string result_headers;
   int code = WebRequest("POST", url, headers, TFE_HTTP_TIMEOUT_MS, post, result, result_headers);
   _tfe_last_check = TimeCurrent();

   if(code == -1)
   {
      int err = GetLastError();
      // Network/permission error -> use grace window if we had a recent allow.
      if(_tfe_last_ok > 0 && (TimeCurrent() - _tfe_last_ok) < TFE_CACHE_GRACE_SECONDS)
      {
         _tfe_last_msg = "Network error (" + (string)err + "); using cached license.";
         return true;
      }
      _tfe_last_msg = "Cannot reach license server (error " + (string)err +
                      "). Allow the URL in Tools > Options > Expert Advisors > WebRequest.";
      return false;
   }

   string resp = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   bool allow = (StringFind(resp, "\"allow\":true") >= 0) || (StringFind(resp, "\"allow\": true") >= 0);
   string msg = _tfe_json_str(resp, "message");
   string reason = _tfe_json_str(resp, "reason");

   if(allow)
   {
      _tfe_last_ok = TimeCurrent();
      _tfe_last_msg = (msg == "" ? "License OK" : msg);
      return true;
   }

   _tfe_last_msg = (msg == "" ? "License denied" : msg) +
                   (reason == "" ? "" : " [" + reason + "]");
   return false;
}

//+------------------------------------------------------------------+
//| Public: initialise licensing in OnInit. Returns false to abort.  |
//+------------------------------------------------------------------+
bool TFE_LicenseInit(const string key, const string server, const string product)
{
   // Strategy Tester cannot use WebRequest; allow trading logic to be backtested.
   // Live/demo real-time runs still enforce licensing normally.
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
   {
      _tfe_allowed = true;
      _tfe_last_ok = TimeCurrent();
      _tfe_last_msg = "Tester mode: license check bypassed.";
      return true;
   }

   _tfe_key     = key;
   _tfe_server  = server;
   _tfe_product = product;
   _tfe_key_file = _tfe_license_file(_tfe_product);
   _tfe_key_loaded = false;
   _tfe_last_ok = 0;

   StringTrimLeft(_tfe_key);
   StringTrimRight(_tfe_key);

   // A key entered in the EA inputs always takes priority. If the input is
   // empty, reuse the last server-approved key remembered for this product.
   if(_tfe_key == "")
   {
      _tfe_key = _tfe_load_key();
      _tfe_key_loaded = (_tfe_key != "");
      if(_tfe_key_loaded)
         Print("TFE License: using remembered key from MQL5/Files/", _tfe_key_file, ".");
   }

   // Trim a trailing slash on the server URL.
   if(StringLen(_tfe_server) > 0 && StringGetCharacter(_tfe_server, StringLen(_tfe_server)-1) == '/')
      _tfe_server = StringSubstr(_tfe_server, 0, StringLen(_tfe_server)-1);

   if(_tfe_key == "")
   {
      Print("TFE License: no license key set. Enter your key in the EA inputs.");
      Comment("TheFinanceEngine — LICENSE KEY MISSING\nEnter your license key in the EA inputs.");
      _tfe_allowed = false;
      return false;
   }

   _tfe_allowed = _tfe_call_server();
   if(!_tfe_allowed)
   {
      Print("TFE License: activation failed -> ", _tfe_last_msg);
      Comment("TheFinanceEngine — LICENSE INACTIVE\n" + _tfe_last_msg);
   }
   else
   {
      // Never persist an unverified key. A manually entered key is remembered
      // only after the license server has approved it.
      if(!_tfe_key_loaded && _tfe_save_key(_tfe_key))
         Print("TFE License: key remembered in MQL5/Files/", _tfe_key_file, ".");
      Print("TFE License: active. ", _tfe_last_msg);
      Comment("");
   }
   return _tfe_allowed;
}

//+------------------------------------------------------------------+
//| Public: call every tick. Cheap; only hits server on heartbeat.   |
//| Returns whether trading is currently permitted.                  |
//+------------------------------------------------------------------+
bool TFE_LicenseOK()
{
   // In the Strategy Tester / optimizer, licensing is bypassed (see TFE_LicenseInit).
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
      return true;

   if(_tfe_key == "") return false;

   if((TimeCurrent() - _tfe_last_check) >= TFE_HEARTBEAT_SECONDS)
   {
      _tfe_allowed = _tfe_call_server();
      if(!_tfe_allowed)
         Comment("TheFinanceEngine — LICENSE INACTIVE\n" + _tfe_last_msg);
      else
         Comment("");
   }
   return _tfe_allowed;
}

string TFE_LicenseMessage() { return _tfe_last_msg; }
