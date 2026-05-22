import pandas as pd

df=pd.read_parquet("./FILES/listing_015_sheet1.parquet")

print(df.shape)


print(df.columns)

#df.to_csv('./scontrinato_050_clean.csv',sep=';')
print("fine")
