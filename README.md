# 🛒 CatManDo - Category Management DSS

## 📖 Descrizione del Progetto
**CatManDo** è una pipeline analitica avanzata progettata per supportare i Category Manager della GDO nelle decisioni strategiche di assortimento. 

Invece di basarsi su gerarchie merceologiche statiche, il sistema analizza i dati reali degli scontrini (Transaction & Household) per comprendere il vero comportamento d'acquisto dei consumatori. Tramite algoritmi statistici, simula gli impatti economici (Fatturato, Volumi e Margine) derivanti da modifiche allo scaffale, separando accuratamente le vendite incrementali ("On Top") da quelle cannibalizzate o a rischio.

## ⚙️ Funzionalità Principali (Pipeline)
Il sistema è orchestrato in macro-moduli sequenziali:

1. **ETL & Data Ingestion:** Estrazione incrementale e a blocchi dei dati storici di vendita, anagrafiche articoli e PDV dal Data Warehouse Oracle.
2. **Motori Statistici:**
   * **Similarity (Yule's Q):** Identifica i veri prodotti sostituti confrontando l'associazione a livello di cliente vs. scontrino.
   * **Clustering:** Raggruppamento gerarchico (Ward) dei prodotti in famiglie di bisogno omogenee.
   * **Loyalty:** Calcolo degli indici di fedeltà per stimare le vendite a rischio.
3. **Motori Decisionali (Simulazioni):**
   * **Delisting:** Identificazione prodotti inefficienti e stima del trasferimento vendite.
   * **Aumento:** Espansione dell'assortimento esistente verso nuovi cluster di negozi.
   * **Listing:** Inserimento di nuovi prodotti basato su "Look-alike" con i dati di mercato (IRI).
4. **Stima Impatti & Consolidamento:** Calcolo della cannibalizzazione, Quality Assurance matematica e scrittura massiva dei risultati su DB.

## 🛠️ Tech Stack & Architettura
- **Linguaggio:** Python 3.x
- **Data Processing:** Pandas, NumPy, SciPy (Clustering)
- **Database As-Is:** Oracle DWH (tramite `cx_Oracle` / `oracledb` e `SQLAlchemy`)
- **Reporting As-Is:** Tableau (export in `.hyper` tramite `pantab`)
- **Evoluzione Cloud (To-Be):** Azure Databricks (Compute/Orchestration), Azure Data Lake Gen2 (Storage Parquet), Azure PostgreSQL + Django/React (WebApp BI).

## 📂 Struttura del Progetto (Principale)
* `catman_pipeline.py`: Main controller e orchestratore del flusso.
* `utils.py`: Funzioni di utility, lettura configurazioni.
* `db_manager.py`: Modulo di connessione Oracle, data ingestion e bulk insert.
* `/config/`: File YAML per configurazione DB, categorie merceologiche e mapping output.
* `00metadata.py` -> `10stimaImpatti.py`: I core script per la logica algoritmica di Category Management.
