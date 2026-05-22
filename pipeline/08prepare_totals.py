# -*- coding: utf-8 -*-
# # Totals of current scenario at category and region level
import sys
import pandas as pd
import re
import os
import time
import utils as utl

sku_sales_agg_file = 'cno_sales_by_sku_reg_clus.csv'
category_meta2 = 'Categoria CNO'
category_iri2 = 'Categoria IRI'

config = utl.get_Config()
input_path = config['paths']['input_path']
# sales_path = config['paths']['sales_path']
workarea_path = config['paths']['workarea_path']

# files to process
lookup_file = input_path + config['files']['lookup_cats']

# log_file = config['files'].get('logging_file')
# if log_file is None:
#     log_file = "log_Modulo3.txt"

# run_cfg = config['files']['cat_config']
# 
# with open(run_cfg, "r") as f:
#     cat_config = yaml.safe_load(f)
# 
# categories_to_keep = cat_config['cat_to_run']

# Define column names
lista_colonne = utl.get_Config_Colonne()
group_key = lista_colonne['group_key']
category_meta = lista_colonne['category_meta']
category_iri = lista_colonne['category_iri']
sku_id = lista_colonne['sku_id']
sku_desc = lista_colonne['sku_desc']
cust_id = lista_colonne['cust_id']
pdv_id = lista_colonne['pdv_id']
tx_id = lista_colonne['tx_id']
tx_date = lista_colonne['tx_date']
amount = lista_colonne['amount']
qty = lista_colonne['qty']
pop_cluster = lista_colonne['pop_cluster']

def smart_load_to_pd(fname, sep, decimal, encoding):
    _, file_ext = os.path.splitext(fname)
    if file_ext == "zip":
        return pd.read_csv(fname, compression='zip', sep=sep, decimal=decimal, encoding=encoding)
    else:
        return pd.read_csv(fname, sep=sep, decimal=decimal, encoding=encoding)

cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal= ".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
cat_lookup = cat_lookup.sort_values(by="sales_2y")

nosales_cat = []

def process_single_category(cat: str):

    # print("===============")
    # print("SCRIPT - totals")
    # print("===============")

    start_tot = time.time()
    print("Running totals calculation for category: " + str(cat))
    cat_out = workarea_path + re.sub("/", "", str(cat))
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    sku_filter = workarea_path + re.sub("/", "", str(cat)) + "/" + config['files']['sku_filter']
    sku_sales_agg = workarea_path + re.sub("/", "", str(cat)) + "/" + sku_sales_agg_file
    cat_tot = cat_out + 'totals' + '_' + str(cat_code).zfill(3) + ".csv"
    if not os.path.exists(sku_filter) or not os.path.exists(sku_sales_agg):
        nosales_cat.append(cat)
        return
    #
    print("Totals: step 1 - import")
    # Import helper metadata
    hlpr_cols2use = [
        sku_id, sku_desc, 'Settore', category_iri, category_meta, group_key, 'Regione', pop_cluster
        ]
    sku_flt = pd.read_csv(sku_filter, sep=";", decimal= ",")
    sku_flt = sku_flt[hlpr_cols2use].drop_duplicates()
    #print(sku_flt.shape) #1412
    sku_flt = sku_flt[sku_flt[category_meta] == re.sub("_", " ", str(cat))]
    sku_flt = sku_flt.rename(columns = {
        category_iri: category_iri2,
        category_meta: category_meta2,
        sku_id: 'Articolo Radice_COD'
        }
    )
    # Import sales data aggregated at SKU, region and cluster level
    sales_by_sku_reg_clus = pd.read_csv(sku_sales_agg, sep=";", decimal= ",")
    #print(sales_by_sku_reg_clus.shape)
    # Merge total sales with sku_flt
    sales_by_sku_reg_clus = sales_by_sku_reg_clus.merge(
        sku_flt,
        on = ['Articolo Radice_COD', 'Settore', category_iri2, group_key, 'Regione', pop_cluster]
    )
    #print(sales_by_sku_reg_clus.shape)
    #
    print("Totals: step 2 - sales aggregations")
    # Calculate total aggregated sales
    total_sales = sales_by_sku_reg_clus.groupby(
        ['Settore', category_meta2, category_iri2, 'Regione']
        ).agg({
            'total_sellout_revenues': 'sum',
            'total_sellout_volume': 'sum',
            'total_margin_cost': 'sum',
            'total_margin_sold': 'sum'
        }
    )
    total_sales['Margine totale'] = total_sales['total_margin_sold'] - total_sales['total_margin_cost']
    total_sales['Margine pct'] = total_sales['Margine totale'] / total_sales['total_margin_sold']
    total_sales = total_sales.drop(columns = ['total_margin_cost', 'total_margin_sold'])
    total_sales = total_sales.rename(columns = {
        'total_sellout_revenues': 'Fatturato totale',
        'total_sellout_volume': 'Volumi totali',
        }
    )
    total_sales = total_sales.fillna(0)
    total_sales = total_sales.reset_index()
    print("total_sales shape: ", total_sales.shape)
    # Save results
    total_sales.to_csv(cat_tot, index=False, sep=";", decimal= ",")
    del total_sales
    del sales_by_sku_reg_clus
    del sku_flt


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python metadata.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    current_category = sys.argv[1]

    process_single_category(current_category)

    sys.exit(0)  # Esce indicando successo
