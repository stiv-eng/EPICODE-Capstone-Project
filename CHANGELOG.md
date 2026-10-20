# Release v0.2.0 — 2026-10-15

## Nuove funzioni
- Frontend Streamlit multipagina senza modifiche ai file legacy.
- Lap/stint dashboard con ranking e distribuzione dei lap times.
- Cronologia stint/compound e regressione lineare esplorativa sui giri gomma.
- Confronto due giri telemetrici (Speed, Throttle, Brake, RPM, nGear).
- Grafico del delta tempo cumulato B-A sullo stesso asse distanza.
- Mappa XY con colorazione speed e hover interattivo.
- Selettore condiviso di stagione, GP e sessione e cache locale FastF1.
- Valutazione quantitativa del modello Q su dati mai usati in training.
- Report MAE macro per giro / fase e export CSV Q.
- Metriche macro FP su validazione raggruppata per giro.
- Normalizzazione dello zero dei tempi telemetrici al primo campione.
- Suite di test sintetici ampliata a 10 test.

## Non modificato / non verificato
- Il codice legacy del repository GitHub non è stato letto o modificato.
- Replay e modello principale restano quelli del prototipo v0.1 con migliorie sopra.
- Non eseguito l'avvio completo FastF1 + Streamlit con un weekend reale.

## 0.3.0 — integrazione repository originali
- Letti i file originali su GitHub tramite plugin con permessi di scrittura.
- Porting SVR da Codes/Page_3.py, con pipeline scikit-learn e nuova pagina Streamlit.
- Protezione del repository originale: codice scritto solo su branch nel Capstone.
- Test smoke aggiuntivo e manuale per lo studio del codice.
