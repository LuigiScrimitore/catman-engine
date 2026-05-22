import pantab as pt
from tableauhyperapi import TableName

table = TableName("Extract", "Extract")

dtfrm=pt.frame_from_hyper("stima_impatti_all.hyper", table=table)
print(dtfrm.shape)

dtfrm.to_csv('./stima_impatti_all_29.csv',sep=';')

