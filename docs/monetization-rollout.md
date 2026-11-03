# DealRadar Schweiz – Umsetzung der 20 Monetarisierungsmassnahmen
Stand: 2026-11-03. Keine Umsatz- oder Verifizierungsbehauptungen ohne Nachweis.

## Reihenfolge und Abhängigkeiten
1. Affiliate-Programme: Awin und Adtraction geprüft; persönliche Anmeldung / Bestätigung offen. Keine echte Publisher-ID vorhanden.
2. Schweizer Top-Deals: site/deals.json ist zunächst LEER. Angebote erst nach Live-Preis-/Versandprüfung eintragen.
3. Comedy mit Kaufanreiz: CTA zur Angebotsseite, aber nie Fake-Preise oder erfundene Rabatte.
4. Kostenlose Website: site/index.html erstellt. GitHub Pages / Domain / Deployment und Live-URL stehen noch aus.
5. Händleransprache: Angebotsentwurf vorbereiten; nur mit echten Referenzen, keine erfundenen Reichweitenzahlen.
6. Zwei bis drei Videos täglich: erst A/B-Test, dann nach beobachteter Wiedergabedauer und Conversion skalieren.
7. Instagram: Kontoverbindung und Veröffentlichungsrechte prüfen.
8. YouTube: Kontoverbindung und Veröffentlichungserlaubnis prüfen.
9. Telegram: Kanal nur nach Plattform-Authentifizierung anlegen.
10. WhatsApp: Kanal nur nach expliziter Konto-/Berechtigungsprüfung anlegen.
11. Newsletter: Opt-in, Datenschutz, Abmeldung und Zustelldienst einrichten.
12. Gesponserte Deals: nur klar als Werbung bezeichnet.
13. Preisfehler-Radar: verlässliche Vergleichsdaten + Prüfregel; ohne Produktbeleg keine Meldung.
14. Preisvergleich: nur mit zulässigen Produktdaten und beobachteter Verfügbarkeit.
15. Premium-Preisalarme: erst nach bewiesener Zustellung und Preisaktualität starten.
16. SEO-Ratgeber: einzigartige, überprüfte Inhalte.
17. Saisonaktionen: Black Friday, Weihnachten – echte Belege.
18. Werbeflächen: erst bei belastbarem Traffic.
19. Videodienstleistung: Angebot CHF 250–500 für 5 Clips nur als unverbindlicher Testpreis, kein Marktpreisversprechen.
20. Automatisierung: Quelle → Validierung → Produktion → QA → Upload → Scheduling → Reporting, mit Duplikatschutz.

## Affiliate-Kandidaten
- Awin: https://www.awin.com/ch/affiliate-marketing/publisher-werden
- Adtraction: https://adtraction.com/ch/partner/
Eigene Registrierung, E-Mail-Verifikation und Bankdaten werden nicht simuliert; keine Zugangsdaten im Repository ablegen.

## Messmodell
UTM-Felder: utm_source=(tiktok|instagram|youtube|newsletter), utm_medium=social, utm_campaign=dealradar, utm_content=<video-id>. Ohne Analytics-Connector sind keine echten Conversions ermittelbar.
Kennzahlen: Videoaufrufe, 3-Sekunden-Retention, Abschlussrate, Profilbesuche, Linkklicks, Händlerklicks, bestätigte Sales, Auszahlung, Kosten, Deckungsbeitrag.
Reporting: keine Annahmen als Ist-Werte ausgeben.

## Veröffentlichung und Sicherheit
Der aktuelle GitHub-Actions-Workflow rendert MP4; Metricool ist als ChatGPT-Connector verbunden, aber der unbeaufsichtigte GitHub→Metricool-Transfer ist nicht bestätigt. Keine falschen Automatisierungsbehauptungen.
