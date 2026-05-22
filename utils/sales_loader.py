"""
utils/sales_loader.py
---------------------
Funzioni centralizzate per il caricamento e la discovery dei file sales.

Sostituisce le copie duplicate presenti in:
  - pipeline/01prefiltering.py
  - pipeline/02similarity.py
  - pipeline/03cluster.py
  - pipeline/04loyalty.py
"""

import os
import re

import pandas as pd


# ---------------------------------------------------------------------------
# Costanti per i filtri loyalty
# ---------------------------------------------------------------------------

_LOYALTY_COLUMNS = [
    'ART_RADICE_COD', 'PDV_COD', 'CUSTOMER_ID', 'DATA_SCONTRINO',
    'QUANTITA', 'IMPORTO', 'PROMO_FLAG', 'FIDELITY_FLAG'
]

_LOYALTY_FILTERS = [
    ('PROMO_FLAG',   '=',  0),
    ('FIDELITY_FLAG','=',  1),
    ('CUSTOMER_ID',  '!=', '-1'),
]


# ---------------------------------------------------------------------------
# load_filtered_sales_parquet
# ---------------------------------------------------------------------------

def load_filtered_sales_parquet(filepath, start_date=None, end_date=None,
                                 apply_loyalty_filters=False):
    """
    Carica un file Parquet applicando filtri temporali e, opzionalmente,
    filtri specifici per l'analisi loyalty (PROMO_FLAG, FIDELITY_FLAG,
    CUSTOMER_ID).

    Args:
        filepath (str): Percorso del file Parquet.
        start_date (str, optional): Data di inizio filtro ('YYYY-MM-DD').
        end_date (str, optional): Data di fine filtro ('YYYY-MM-DD'), inclusivo.
        apply_loyalty_filters (bool): Se True applica i filtri loyalty e
            seleziona solo le colonne necessarie all'analisi loyalty.

    Returns:
        pd.DataFrame
    """
    if apply_loyalty_filters:
        # Filtri loyalty: no promo, solo fidelity, escludi customer fittizio
        filters = list(_LOYALTY_FILTERS)
        if start_date:
            filters.append(('DATA_SCONTRINO', '>=', start_date))
        df = pd.read_parquet(
            filepath,
            columns=_LOYALTY_COLUMNS,
            filters=filters,
            engine='pyarrow'
        )
    else:
        filters = []
        if start_date:
            filters.append(('DATA_SCONTRINO', '>=', start_date))
        if end_date:
            filters.append((
                'DATA_SCONTRINO', '<=',
                pd.Timestamp(end_date) + pd.Timedelta(days=1, microseconds=-1)
            ))
        if filters:
            df = pd.read_parquet(filepath, filters=filters)
        else:
            print("Nessun filtro temporale specificato, caricamento dell'intero file.")
            df = pd.read_parquet(filepath)

    return df


# ---------------------------------------------------------------------------
# smart_load_to_pd
# ---------------------------------------------------------------------------

def smart_load_to_pd(fname, sep, decimal, encoding, spec_types=None,
                      apply_loyalty_filters=False):
    """
    Carica un file dati rilevando automaticamente il formato
    (parquet, zip, csv).

    Per i file parquet applica un filtro temporale minimo per limitare
    l'uso di memoria. Se apply_loyalty_filters=True vengono applicati
    anche i filtri specifici per l'analisi loyalty.

    Args:
        fname (str): Percorso del file.
        sep (str): Separatore CSV.
        decimal (str): Separatore decimale CSV.
        encoding (str): Encoding CSV.
        spec_types (dict, optional): Tipi colonna da forzare in lettura CSV.
        apply_loyalty_filters (bool): Attiva i filtri loyalty per parquet.

    Returns:
        pd.DataFrame
    """
    _, file_ext = os.path.splitext(fname)
    if spec_types is None:
        spec_types = {}

    if file_ext == ".zip":
        return pd.read_csv(
            fname, compression='zip', sep=sep, decimal=decimal,
            encoding=encoding, dtype=spec_types
        )

    elif file_ext == ".parquet":
        # Il file scont_l2y_050 è molto grande: limitiamo la finestra temporale
        if 'scont_l2y_050.parquet' in fname:
            min_data = '2024-05-04'
            print('BIG FILE!!!')
        else:
            min_data = '2022-01-01'

        df = load_filtered_sales_parquet(
            fname, min_data,
            apply_loyalty_filters=apply_loyalty_filters
        )
        print(df.shape)
        return df

    else:
        return pd.read_csv(
            fname, sep=sep, decimal=decimal, encoding=encoding,
            dtype=spec_types, low_memory=True
        )


# ---------------------------------------------------------------------------
# get_sales_files
# ---------------------------------------------------------------------------

def get_sales_files(sales_path, cat_code):
    """
    Individua i file sales per una categoria applicando la seguente
    priorità:
      1. File parquet singolo legacy:  scont_l2y_{cat_code}.parquet
      2. File CSV singolo:             SALES_2Y_CAT{cat_code}.csv
      3. File CSV multipli (chunked):  SALES_2Y_CAT_{cat_code}_GRP.*.csv

    Args:
        sales_path (str): Cartella base dei file sales (con slash finale).
        cat_code (int | str): Codice categoria (verrà zero-padded a 3 cifre).

    Returns:
        tuple(list[str], bool):
            - lista ordinata dei file trovati (percorsi completi)
            - multi_sales: True se sono stati trovati file multipli (chunked)
    """
    code = str(cat_code).zfill(3)

    # 1. Parquet singolo legacy
    parquet_single = sales_path + "scont_l2y_" + code + ".parquet"
    if os.path.exists(parquet_single):
        return [parquet_single], False

    # 2. CSV singolo
    csv_single = sales_path + "SALES_2Y_CAT" + code + ".csv"
    if os.path.exists(csv_single):
        return [csv_single], False

    # 3. CSV multipli (chunked)
    pattern = re.compile(r"SALES_2Y_CAT_" + code + r"_GRP.*.csv")
    chunked = sorted([
        sales_path + ff
        for ff in os.listdir(sales_path)
        if pattern.search(ff) is not None
    ])
    return chunked, True
