#!/usr/bin/env python3
"""DealRadar daily status: no credentials or fabricated revenue required."""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

def get_json(url, token=None):
    headers={"User-Agent":"DealRadar-DailyReport/1.0","Accept":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=15) as response:
        return json.load(response)

def report():
    now=datetime.now(ZoneInfo("Europe/Zurich"))
    lines=[f"🇨🇭 DealRadar Tagesreport · {now:%d.%m.%Y %H:%M}",""]
    url=os.getenv("CLICK_REPORT_URL","").strip()
    token=os.getenv("CLICK_REPORT_TOKEN","").strip()
    if url and token:
        try:
            data=get_json(url,token)
            if not isinstance(data.get("rows"),list): raise ValueError("Ungültiges Klick-Report-Format")
            rows=data["rows"]
            total=sum(int(x.get("clicks") or 0) for x in rows)
            lines.append(f"Gemessene Weiterleitungsklicks (7 Tage): {total}")
            if rows:
                best=max(rows,key=lambda x:int(x.get("clicks") or 0))
                lines.append(f"Top-Klickquelle: Video {best.get('video','unbekannt')} · Produkt {best.get('link_id','unbekannt')} · {int(best.get('clicks') or 0)} Klicks")
            else: lines.append("Noch keine gespeicherten Klicks.")
        except Exception as e:
            lines.append("Klicks: nicht messbar (Abruf fehlgeschlagen)")
            print("Click report error:",type(e).__name__,file=sys.stderr)
    else: lines.append("Klicks: nicht messbar (CLICK_REPORT_URL / CLICK_REPORT_TOKEN fehlen)")
    lines.extend(["TikTok-Aufrufe: nicht messbar (kein verifizierter Datenadapter)","Awin-Provision CHF: nicht messbar (kein verifizierter Datenadapter)","Awin-Provision EUR: nicht messbar (kein verifizierter Datenadapter)","Nächster Schritt: Affiliate-Datenquelle verbinden und echte Klickzuordnung testen."])
    return "\n".join(lines)

def main():
    message=report()
    print(message)
    bot=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat=os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not (bot and chat):
        print("Telegram nicht konfiguriert; Trockenlauf abgeschlossen.",file=sys.stderr)
        return 0
    data=json.dumps({"chat_id":chat,"text":message,"disable_web_page_preview":True}).encode()
    request=urllib.request.Request("https://api.telegram.org/bot"+bot+"/sendMessage",data=data,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            result=json.load(response)
            if not result.get("ok"): raise RuntimeError("Telegram rejected request")
    except Exception as e:
        print("Telegram delivery failed:",type(e).__name__,file=sys.stderr)
        return 1
    print("Telegram delivery accepted.")
    return 0

if __name__=="__main__": raise SystemExit(main())
