import os
import re
import sys
import pandas as pd
import numpy as np
import yaml
import utils as utl

#DEFINIZIONE VARIABILI
category_meta= "Categoria Merceologica"
category_iri= "Categoria"
sku_status= "ART_STATO_DESC"
sku_score= "PRIORITA' ASSORTIMENTO COMPLESSIVO"
group_key= "Tipo-Varieta"


# config_file = "./config/configurazioni.yaml"
# with open(config_file, "r") as f:
#     config = yaml.safe_load(f)

config = utl.get_Config()

# files to process
# meta_path = config['paths']['meta_path']
workarea_path= config['paths']['workarea_path']
input_path= config['paths']['input_path']
anag_file = input_path + config['files']['pdv']
clus_file = input_path + config['files']['clusters']
meta_file = input_path + config['files']['metadata']
lookup_file = input_path + config['files']['lookup_cats']
#meta_file="./input/OTTOBRE/Metadati_DB.csv"

empty_cat = []
noclus_cat = []

# print(input_path)
# print(workarea_path)
# print(anag_file)
# print(clus_file)
# print(meta_file)
# print(lookup_file)

def load_dati(file):
    print(f"carico il file ",file)
    spec_types = {'EAN': object, 'Micro Reparto_COD': object,
                  'Articolo Marchio': object, 'Anno Mobile': object,
                  'ART_STATO_DESC': object, 'Articolo Radice_COD': str}
    sku_meta = pd.read_csv(file, sep=';', decimal='.', encoding='latin-1', dtype=spec_types)

    # PATCH DA APPLICARE SUL DB: i dati non sono b
    sku_meta['Articolo Radice_COD'] = sku_meta['Articolo Radice_COD'].replace('.0', '')
    sku_meta['Prodotto'] = sku_meta['Prodotto'].str.lstrip()
    # condizione_numerica = pd.to_numeric(sku_meta['Prodotto'], errors='coerce').notna()
    #
    # condizione = ((sku_meta['Articolo Radice'].isin(['Mancato Riscontro', 'Non in assortimento CNO'])) &
    #               (sku_meta['Articolo Radice_COD'].isna()) &
    #               (sku_meta['Prodotto']!=sku_meta['Prodotto_Dettaglio']) &
    #               condizione_numerica
    #               )
    #
    # sku_meta.loc[condizione, 'Articolo Radice_COD'] = sku_meta.loc[condizione, 'Prodotto']

    # CEGIL fix temporaneo per i non in assortimento cno
    # sku_meta.loc[
    #     ~(sku_meta[category_meta].isin(['Mancato Riscontro', 'Non in assortimento CNO'])) &
    #     (sku_meta["CNO_AC_Vendite in Valore"] < 1) &
    #     (sku_meta["Cluster" ]=='NO_CLUSTER'),
    #     'Categoria Merceologica'
    # ] = 'Non in assortimento CNO'
    #
    return sku_meta

def ottimizzo(df, object_option=False):
    print("ottimizzo i dati")
    for col in df.columns:
        # process the int columns
        if df[col].dtype == 'int':
            col_min = df[col].min()
            col_max = df[col].max()
            # if all are non-negative, change to uint
            if col_min >= 0:
                if col_max < np.iinfo(np.uint8).max:
                    df[col] = df[col].astype(np.uint8)
                elif col_max < np.iinfo(np.uint16).max:
                    df[col] = df[col].astype(np.uint16)
                elif col_max < np.iinfo(np.uint32).max:
                    df[col] = df[col].astype(np.uint32)
                else:
                    df[col] = df[col]
            else:
                # if it has negative values, downcast based on the min and max
                if col_max < np.iinfo(np.int8).max and col_min > np.iinfo(np.int8).min:
                    df[col] = df[col].astype(np.int8)
                elif col_max < np.iinfo(np.int16).max and col_min > np.iinfo(np.int16).min:
                    df[col] = df[col].astype(np.int16)
                elif col_max < np.iinfo(np.int32).max and col_min > np.iinfo(np.int32).min:
                    df[col] = df[col].astype(np.int32)
                else:
                    df[col] = df[col]
        # process the float columns
        elif df[col].dtype == 'float':
            col_min = df[col].min()
            col_max = df[col].max()
            # downcast based on the min and max
            if col_min > np.finfo(np.float32).min and col_max < np.finfo(np.float32).max:
                df[col] = df[col].astype(np.float32)
            else:
                df[col] = df[col]
        if object_option:
            if df[col].dtype == 'object':
                if len(df[col].value_counts()) < 0.5 * df.shape[0]:
                    df[col] = df[col].astype('category')
    return df

def adatto(sku_meta):
    print("adatto i dati")
    meta_cols2keep = [
        "EAN", "Articolo Radice", "Articolo Radice_COD", "Prodotto", sku_status,
        "Cluster", "Regione", "Canale", "Formato",
        "Categoria", "Categoria Merceologica",
        "Settore", "Settore merceologico",
        "Tipo", "Varieta",
        "Marca", "Fornitore",
        "CNO_AC_Vendite in Valore", "CNO_AC_Vendite in Volume",
        "MKT_AC_Vendite in Valore", "MKT_AC_Vendite in Volume",
        "Margine Costo Netto", "Margine Venduto", 'Importo Sellout', 'SELLOUT_QTA',
        sku_score
    ]
    # keep relevant columns
    sku_meta = sku_meta[meta_cols2keep].astype({
        'Articolo Radice_COD': str,
        'EAN': str
    }).rename(columns={
        'Importo Sellout': 'Sellout Importo',
        'SELLOUT_QTA': 'Sellout Quantita'
    })
    # add group key
    sku_meta['Tipo-Varieta'] = sku_meta['Tipo'] + " / " + sku_meta['Varieta']
    sku_meta['CNO_Margine'] = sku_meta['Margine Venduto'] - sku_meta['Margine Costo Netto']
    sku_meta['CNO_Margine_pct'] = sku_meta['CNO_Margine'] / sku_meta['Margine Venduto']

    return sku_meta


def filtro(df, categoria):
    print("filtro i dati")

    # restrict to few categories (including listing candidates)
    categoria= str.replace(categoria, "_", " ")
    #iri_categs = df[df[category_meta].isin(categoria)][category_iri].drop_duplicates()

    iri_categs = df[df[category_meta] == categoria][category_iri].drop_duplicates()

    # the above contains a few errors due to mismatch in EAN, but we need to live with it
    df = df[(df[category_iri].isin(iri_categs)) &
            (df[category_meta].isin([categoria,'Mancato Riscontro','Non in assortimento CNO']))]

    return df

def fix_non_valid_eans_in_metadata(sku_meta):
    print("fisso gli EAN non validi")

    check_eans = sku_meta.groupby(
        ['Articolo Radice_COD', 'Formato', 'Canale', 'Regione', 'Cluster']
        )['EAN'].nunique(
        ).reset_index(
        ).rename(columns={'EAN': 'n_EANs'})
    # Save the list of non valid EANs
    unknown_eans = sku_meta.merge(
            check_eans[check_eans["n_EANs"]>1],
            on=['Articolo Radice_COD', 'Formato', 'Canale', 'Regione', 'Cluster']
        )['EAN'].unique().tolist()
    #print('Metadata shape for non valid EANs (current): ',
    sku_meta['Articolo Radice_COD']=sku_meta['Articolo Radice_COD'].astype(str)
    sku_meta_fixed_eans = sku_meta.loc[sku_meta['EAN'].isin(unknown_eans)].groupby(
            ['Articolo Radice_COD', 'Formato', 'Canale', 'Regione', 'Cluster'],
            as_index=False
        ).agg({
            'EAN': "min",
            'Articolo Radice': "min",
            'Prodotto': "min",
            sku_status: "min",
            'Categoria': "min",
            'Categoria Merceologica': "min",
            'Settore': "min",
            'Settore merceologico': "min",
            'Tipo': "min",
            'Varieta': "min",
            'Marca': "min",
            'Fornitore': "min",
            'CNO_AC_Vendite in Valore': "min",
            'CNO_AC_Vendite in Volume': "min",
            'MKT_AC_Vendite in Valore': "min",
            'MKT_AC_Vendite in Volume': "min",
            'Margine Costo Netto': "mean",
            'Margine Venduto': "mean",
            'Sellout Importo': "min",
            'Sellout Quantita': "min",
            sku_score: "min",
            group_key: "min",
            'CNO_Margine': "mean",
            'CNO_Margine_pct': "mean"
        })

    #      sku_meta.loc[sku_meta['EAN'].isin(unknown_eans)].shape)
    # Create the meta subset for the non valid EANs, aggregating EAN and margin
    # print('Metadata shape for non valid EANs (fixed, aggregated): ',
    #      sku_meta_fixed_eans.shape)
    # Merge back together
    sku_meta = pd.concat(
        [sku_meta.loc[~sku_meta['EAN'].isin(unknown_eans)],
        sku_meta_fixed_eans])

    #print('Final metadata shape: ', sku_meta.shape)

    return sku_meta

def trova_ean_misti(gruppo):
    # Controlla se 'Non in assortimento CNO' è presente nei cluster del gruppo
    ha_non_assortito = 'Non in assortimento CNO' in gruppo['Cluster'].values

    # Controlla se c'è più di un cluster unico
    ha_piu_cluster = gruppo['Cluster'].nunique() > 1

    # Restituisce True solo se entrambe le condizioni sono verificate
    return ha_non_assortito and ha_piu_cluster

def salva(sku_meta):
    print("salvo i dati")

    # TEST = sku_meta[sku_meta['Cluster']!='Mancato Riscontro']
    # # Applica la funzione di filtro ai gruppi
    # risultato = TEST.groupby(['EAN', 'Regione']).filter(trova_ean_misti)
    #
    # print("\nEAN che in una regione sono sia 'Non in assortimento' che in un altro cluster:")
    # print(risultato)

    cat_out = workarea_path + re.sub("/", "", str(current_category))
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_match = re.sub("_", " ", current_category)
    iri_categs = sku_meta[sku_meta[category_meta] == cat_match][category_iri].drop_duplicates()
    # the above contains a few errors due to mismatch in EAN, but we need to live with it
    sku_meta_red = sku_meta[(sku_meta[category_iri].isin(iri_categs)) &
                            (sku_meta[category_meta].isin([cat_match, 'Mancato Riscontro', 'Non in assortimento CNO']))]
    if (sku_meta_red[~sku_meta_red["ART_STATO_DESC"].isna()]["ART_STATO_DESC"] == "Bloccato").all():
        #empty_cat.append(current_category)
        print("categoria vuota")
        return
    if (sku_meta_red[~sku_meta_red["Cluster"].isna()]["Cluster"].isin(["Mancato Riscontro", "Non in assortimento CNO", "NO_CLUSTER"])).all():
        #noclus_cat.append(current_category)
        print("nessun cluster")
        return
    sku_meta_red['Articolo Radice_COD'] = sku_meta_red['Articolo Radice_COD'].astype(float).fillna('0').astype(int).astype(str)
    print(f'record totali estratti:',sku_meta_red.shape)
    sku_meta_red.to_csv(cat_out + 'metadata_red.csv', index=False, sep=';', decimal='.', encoding='latin-1')


def process_single_category(category: str):
    """
    Funzione che contiene tutta la logica di elaborazione
    per una SOLA categoria.
    """

    #print(f"Eseguo il prepare metadata per la categoria: '{category}'...")
    #
    # QUI VA IL CODICE CHE PRIMA STAVA DENTRO AL TUO LOOP
    # (lettura dati, elaborazione, salvataggio, ecc.)
    #

    # LETTURA METADATI
    sku_meta = load_dati(meta_file)
    sku_meta = ottimizzo(sku_meta)
    sku_meta = filtro(sku_meta, category)
    sku_meta = adatto(sku_meta)
    # sku_meta = fix_non_valid_eans_in_metadata(sku_meta)
    salva(sku_meta)

    #print(f"prepare metadata per '{category}' completato.")


if __name__ == "__main__":
    # Il programma ora si aspetta un argomento dalla riga di comando.
    # sys.argv è una lista che contiene gli argomenti:
    # sys.argv[0] è il nome dello script ("prefiltering.py")
    # sys.argv[1] è il primo argomento (la nostra categoria)

    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python metadata.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    # Prende la categoria dal primo argomento passato
    current_category = sys.argv[1]

    # Lancia l'elaborazione solo per quella categoria
    process_single_category(current_category)

    # Quando lo script termina, il processo viene distrutto e la memoria liberata.
    sys.exit(0)  # Esce indicando successo
