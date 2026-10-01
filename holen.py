"""Holt Kurse von Yahoo Finance und schreibt sie mit Zeitstempel nach kurse.json und kurse.md.
Laeuft automatisch auf GitHub (siehe .github/workflows/kurse.yml)."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import yfinance as yf

ZH = ZoneInfo("Europe/Zurich")

TITEL = {
    # Schweiz
    "SMI": "^SSMI", "SMICHA": "SMICHA.SW",
    "Nestle": "NESN.SW", "Novartis": "NOVN.SW", "Roche": "ROG.SW", "UBS": "UBSG.SW",
    "Richemont": "CFR.SW", "ABB": "ABBN.SW", "Zurich": "ZURN.SW",
    # Sachas Positionen
    "Metaplanet": "3350.T", "XRP_EUR": "XRP-EUR",
    # Umfeld
    "EURCHF": "EURCHF=X", "USDCHF": "USDCHF=X", "USDJPY": "JPY=X", "EURJPY": "EURJPY=X",
    "US10J_Rendite": "^TNX", "Brent": "BZ=F", "Gold": "GC=F", "Bitcoin_USD": "BTC-USD",
    "DAX": "^GDAXI", "SP500": "^GSPC", "Nasdaq": "^IXIC", "Nikkei": "^N225",
    # Watchlist
    "Highlight": "HLG.DE", "Lindt": "LISN.SW", "PartnersGroup": "PGHN.SW", "Sika": "SIKA.SW",
    "SwissLife": "SLHN.SW", "Rheinmetall": "RHM.DE", "Hensoldt": "HAG.DE",
    "Nvidia": "NVDA", "Apple": "AAPL", "Tesla": "TSLA", "Ethereum_EUR": "ETH-EUR",
}


def zh(ts):
    return ts.astimezone(ZH).strftime("%d.%m.%Y %H:%M")


def eintrag(name, ticker):
    t = yf.Ticker(ticker)
    tag = t.history(period="1y", interval="1d", auto_adjust=False)
    if tag.empty:
        return {"name": name, "ticker": ticker, "fehler": "keine Daten"}
    tag = tag.dropna(subset=["Close"])
    intra = t.history(period="1d", interval="5m", auto_adjust=False).dropna(subset=["Close"])
    if not intra.empty:
        kurs = float(intra["Close"].iloc[-1])
        zeit = intra.index[-1].to_pydatetime()
    else:
        kurs = float(tag["Close"].iloc[-1])
        zeit = tag.index[-1].to_pydatetime()
    # Vortagesschluss: letzter Tagesschluss vor dem Handelstag des aktuellen Kurses
    tage = tag[tag.index.date < zeit.date()] if hasattr(zeit, "date") else tag
    vortag = float(tage["Close"].iloc[-1]) if len(tage) else None
    heute = tag[tag.index.date == zeit.date()]
    hoch_schluss_1j = float(tag["Close"].max())
    return {
        "name": name,
        "ticker": ticker,
        "kurs": round(kurs, 6),
        "zeit_zuerich": zh(zeit),
        "zeit_utc": zeit.astimezone(timezone.utc).isoformat(),
        "vortag": round(vortag, 6) if vortag else None,
        "veraenderung_prozent": round((kurs / vortag - 1) * 100, 2) if vortag else None,
        "tageshoch": round(float(heute["High"].iloc[-1]), 6) if len(heute) else None,
        "tagestief": round(float(heute["Low"].iloc[-1]), 6) if len(heute) else None,
        "hoch_schluss_1j": round(hoch_schluss_1j, 6),
        "rueckgang_vom_hoch_prozent": round((1 - kurs / hoch_schluss_1j) * 100, 2),
    }


def main():
    jetzt = datetime.now(timezone.utc)
    daten = {"abgerufen_zuerich": zh(jetzt), "abgerufen_utc": jetzt.isoformat(), "quelle": "Yahoo Finance (verzoegert)", "titel": {}}
    for name, ticker in TITEL.items():
        try:
            daten["titel"][name] = eintrag(name, ticker)
        except Exception as e:  # ein Fehler soll nicht alles stoppen
            daten["titel"][name] = {"name": name, "ticker": ticker, "fehler": str(e)[:200]}

    with open("kurse.json", "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1)

    zeilen = [f"# Kurse, abgerufen {daten['abgerufen_zuerich']} (Zuerich)", "",
              "| Titel | Kurs | Veraenderung % | Stand (Zuerich) | Rueckgang vom 1J Hoch % |", "|---|---|---|---|---|"]
    for d in daten["titel"].values():
        if "fehler" in d:
            zeilen.append(f"| {d['name']} | Fehler: {d['fehler']} | | | |")
        else:
            zeilen.append(f"| {d['name']} | {d['kurs']} | {d['veraenderung_prozent']} | {d['zeit_zuerich']} | {d['rueckgang_vom_hoch_prozent']} |")
    with open("kurse.md", "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")


if __name__ == "__main__":
    main()
