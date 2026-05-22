import numpy as np
import pandas as pd
import re
import yaml
import sys
import os
import argparse

pd.options.mode.chained_assignment = None

## launch with
## > python loyalty_forn.py --config run.yaml

ap = argparse.ArgumentParser()
ap.add_argument("-cfg", "--config", required=False, default=None, help="config file")
args = vars(ap.parse_args())

if args["config"] is None:
    args["config"] = "config.yaml"

with open(args["config"], "r") as f:
    config = yaml.safe_load(f)

#sales_path = config['paths']['data_path']
#meta_path = config['paths']['meta_path']
outp_path = config['paths']['aux_path'] # save files to an "auxiliary file" path

forn_path = "C:/"

categories_to_keep = config['cat_to_run']


def smart_load_to_pd(fname, sep, decimal, encoding, spec_types=None):
    _, file_ext = os.path.splitext(fname)
    if spec_types is None:
        spec_types = {}
    if file_ext == "zip":
        return pd.read_csv(fname, compression='zip', sep=sep, decimal=decimal, encoding=encoding, dtype=spec_types)
    else:
        return pd.read_csv(fname, sep=sep, decimal=decimal, encoding=encoding, dtype=spec_types)


lookup_file = config['paths']['meta_path'] + config['files']['lookup_cats']
cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal= ".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
cat_lookup = cat_lookup.sort_values(by="sales_2y")



in_loyal = []
for cat in categories_to_keep:
    print("Collect loyalty for category: " + str(cat))
    cat_out = outp_path + re.sub("/", "", str(cat)) + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    cat_loyal = cat_out + 'loyalty' + '_' + str(cat_code).zfill(3) +'.csv'
    if not os.path.exists(cat_loyal):
        continue
    tmp = pd.read_csv(cat_loyal, sep=";", decimal= ",")
    tmp["category"] = cat
    tmp["cat_code"] = cat_code
    in_loyal.append(tmp)

in_loyal = pd.concat(in_loyal).reset_index(drop=True)
in_loyal.to_csv(forn_path+"all_loyal.csv", index=False, sep=";", decimal= ",")


in_sales = []
for cat in categories_to_keep:
    print("Collect sales for category: " + str(cat))
    cat_in = outp_path + re.sub("/", "", str(cat)) + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    cat_sales = cat_in + 'sales_per_sku.csv'
    if not os.path.exists(cat_sales):
        print("SBOH " + cat)
        continue
    tmp = pd.read_csv(cat_sales, sep=";", decimal= ",")
    tmp["category"] = cat
    tmp["cat_code"] = cat_code
    in_sales.append(tmp)

in_sales = pd.concat(in_sales)

in_sales.to_csv(forn_path+"all_sales.csv", index=False, sep=";", decimal= ",")


### LOYALTY FORNITORI
meta_file = forn_path+"Metadati.csv"
name_file = forn_path+"2411_Estrazione per calcolo Livello Loyalty.csv"

in_sales = pd.read_csv(forn_path+"all_sales.csv", sep=";", decimal= ",").rename(columns = { "sku_id": "ART_RADICE_COD" })
in_sales["cat_code"] = in_sales["cat_code"].astype(int)

in_loyal = pd.read_csv(forn_path+"all_loyal.csv", sep=";", decimal= ",")
in_loyal["cat_code"] = in_loyal["cat_code"].astype(int)


metadata = smart_load_to_pd(fname=meta_file, sep=',', decimal='.', encoding='latin-1', 
                spec_types={'EAN':object, 'Micro Reparto_COD':object, 
                    'Articolo Marchio':object, 'Anno Mobile':object, 
                    'ART_STATO_DESC':object})
meta_cols2keep = [
        "EAN", "Articolo Radice", "Articolo Radice_COD", 
        "Prodotto", "ART_STATO_DESC",
        "Categoria Merceologica", "Categoria Merceologica_COD",
        "Fornitore",
        "CNO_AC_Vendite in Valore", "CNO_AC_Vendite in Volume",
        "MKT_AC_Vendite in Valore", "MKT_AC_Vendite in Volume",
        'Importo Sellout', 'Importo Sellout Promo'
    ]
metadata = metadata[meta_cols2keep].rename(
    columns = { "Articolo Radice_COD": "ART_RADICE_COD", "Categoria Merceologica": "category", "Categoria Merceologica_COD": "cat_code" }
)
metadata_gp = metadata[
    (metadata.ART_STATO_DESC=="Attivo") & (~metadata.category.isna())
].groupby([
    "EAN",
    "Articolo Radice",
    "ART_RADICE_COD", 
    "Prodotto",
    "ART_STATO_DESC",
    "category",
    "cat_code",
    "Fornitore"
]).sum().reset_index()

metadata_gp["ART_RADICE_COD"] = metadata_gp["ART_RADICE_COD"].astype(int)
metadata_gp["cat_code"] = metadata_gp["cat_code"].astype(int)
metadata_gp["category"] = metadata_gp["category"].str.replace(" ", "_")


## join sales & loyalty
master = metadata_gp.merge(
    in_sales, 
    on=["ART_RADICE_COD", "category", "cat_code"], 
    how="inner"
).merge(
    in_loyal, 
    on=["ART_RADICE_COD", "category", "cat_code"], 
    how="inner"
)
master = master.rename(columns = {
    "avg_monthly_revenues":"sku_sell",
    "tot_pieces":"num_pieces",
})
master["ART_RADICE_COD"] = master["ART_RADICE_COD"].astype(int)

## load providers with fixed names
hlpr = smart_load_to_pd(fname=name_file, sep=',', decimal='.', encoding='latin-1').rename(
    columns = {
        "Articolo Radice_COD": "ART_RADICE_COD",
        "Categoria Merceologica": "category",
        "Categoria Merceologica_COD": "cat_code" 
    }
)
## separate handling for private label
hlpr["FornitoreReduced"] = hlpr["Fornitore Principale"]
hlpr.loc[(hlpr["PAM_FLAG"] > 0) | hlpr["Fornitore Principale"].str.contains("CONAD"), "FornitoreReduced"] = "Private Label CNO"
hlpr["category"] = hlpr["category"].str.replace(" ", "_")
hlpr["cat_code"] = hlpr["cat_code"].astype(str).str.zfill(3)

master_red = master.merge(
    hlpr[
            [
                "ART_RADICE_COD",
                "category",
                "cat_code",
                "Fornitore Principale_COD",
                "Fornitore Principale",
                "FornitoreReduced"
            ]
        ].rename(
            columns={"Articolo Radice_COD":"ART_RADICE_COD"} 
        ).drop_duplicates(), 
    on=["ART_RADICE_COD", "category", "cat_code"], 
    how="outer"
)



## create additional variables
master_red["tot_sell"] = master_red.groupby(["cat_code", "FornitoreReduced"])["sku_sell"].transform('sum')
master_red["loyalty_sellout"] = master_red["loyalty"] * master_red["sku_sell"] / master_red["tot_sell"]
master_red["loyalty_forn"] = master_red.groupby(["cat_code", "FornitoreReduced"])["loyalty_sellout"].transform(lambda x : 
        x[x>=0.0].sum() if (x>=0.0).sum()>0 else np.nan)

out_df = master_red.groupby(["cat_code", "category", "Fornitore Principale_COD", "Fornitore Principale"])['loyalty_forn'].\
                    first().reset_index().rename(columns={'cat_code':'Categoria Merceologica_COD', 
                                                            'category':'Categoria Merceologica', 
                                                            'loyalty_forn':'loyalty_sellout_strict'})
out_df["min_forn"] = out_df.groupby(['Fornitore Principale'])["loyalty_sellout_strict"].transform("min")
out_df["loyalty_sellout"] = out_df["loyalty_sellout_strict"]
out_df.loc[(out_df["loyalty_sellout"].isna()) & (~out_df["min_forn"].isna()), "loyalty_sellout"] = out_df["min_forn"]

out_df[["Categoria Merceologica_COD", "Categoria Merceologica", 
        "Fornitore Principale_COD", "Fornitore Principale", 
        "loyalty_sellout_strict", "loyalty_sellout"]].to_excel(forn_path+"FornitoriLoyalty_Nov2024.xlsx", index=False)

