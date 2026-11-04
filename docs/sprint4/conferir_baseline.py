from pathlib import Path
import json,hashlib,sys
import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
root=Path(__file__).resolve().parents[2]
src=root/'sprint3'
df=pd.read_csv(src/'sprint2_core/dataset_motor_sprint2_bruto.csv')
classes=['normal','monitoramento','alerta','critico']
oper=df[df.classe_manutencao.isin(classes)]
y=oper.classe_manutencao.map({c:i for i,c in enumerate(classes)}).to_numpy()
train,test=train_test_split(np.arange(len(y)),test_size=0.2,stratify=y,random_state=42)
major=int(np.bincount(y[train]).argmax())
pred=np.full(len(test),major)
result={'version':'1.5','consolidation_date':'2026-11-03','scope':'Baseline documental calculada nesta revisão; sem retreino ou execução de RF/VQC.','split':'Reconstruído do protocolo de train_and_persist.py: classes operacionais em ordem do CSV, rótulos inteiros, test_size=0.2, stratify=y, random_state=42. Índices históricos não foram fornecidos; identidade exata com a execução antiga não é certificável.','n_train':len(train),'n_test':len(test),'majority_chosen_from_train':classes[major],'train_class_counts':{c:int((y[train]==i).sum()) for i,c in enumerate(classes)},'test_class_counts':{c:int((y[test]==i).sum()) for i,c in enumerate(classes)},'correct_predictions':int((pred==y[test]).sum()),'accuracy':float(accuracy_score(y[test],pred)),'f1_macro':float(f1_score(y[test],pred,average='macro',labels=range(4),zero_division=0)),'f1_per_class':dict(zip(classes,map(float,f1_score(y[test],pred,average=None,labels=range(4),zero_division=0)))),'confusion_matrix':confusion_matrix(y[test],pred,labels=range(4)).tolist(),'test_csv_data_indices_zero_based':oper.index.to_numpy()[test].tolist(),'versions':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__,'scikit-learn':sklearn.__version__},'source_sha256':{p.relative_to(src).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [src/'train_and_persist.py',src/'sprint2_core/dataset_motor_sprint2_bruto.csv']}}
# Audit the raw-reading support of each causal maintenance window [i-19, i].
# Use original CSV indices: filtering operational rows must not compress time.
train_raw=oper.index.to_numpy()[train]
test_raw=oper.index.to_numpy()[test]
train_start=np.maximum(0,train_raw-19)
test_start=np.maximum(0,test_raw-19)
intersections=(train_start[None,:]<=test_raw[:,None]) & (train_raw[None,:]>=test_start[:,None])
later_contains=(train_raw[None,:]>test_raw[:,None]) & (train_start[None,:]<=test_raw[:,None])
overlap_count=intersections.sum(axis=1)
later_count=later_contains.sum(axis=1)
def count_stats(values):
    return {'min':int(values.min()),'max':int(values.max()),'mean':float(values.mean()),'total_pairs':int(values.sum())}
result['version']='1.5'
result['temporal_overlap_maintenance']={
    'window_readings':20,'window_support':'[max(0, i-19), i], inclusive; i is the original zero-based CSV data-row index',
    'n_train_windows':len(train_raw),'n_test_windows':len(test_raw),
    'test_windows_with_training_intersection':int((overlap_count>0).sum()),
    'fraction_with_training_intersection':float((overlap_count>0).mean()),
    'overlapping_train_windows_per_test':count_stats(overlap_count),
    'later_train_windows_containing_test_reading':count_stats(later_count),
    'train_csv_data_indices_zero_based':train_raw.tolist(),
    'overlap_counts_in_test_index_order':overlap_count.tolist(),
    'later_counts_in_test_index_order':later_count.tolist(),
    'scope':'Full 3,952-row reconstructed training partition used by RF, before the VQC 400-row subsample; these counts are not asserted for that subsample.',
    'interpretation':'Causal rolling features do not make a random split temporally independent. Test readings contribute to later training windows. This audit does not estimate metric inflation or reproduce historical model predictions.'}
out=root/'docs/sprint4/baseline_majoritaria_manutencao.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='test_csv_data_indices_zero_based'},ensure_ascii=True,indent=2))
