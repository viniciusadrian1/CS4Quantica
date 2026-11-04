from pathlib import Path
import ast,json,hashlib,sys
import numpy as np
import pandas as pd

root=Path(__file__).resolve().parents[2]
src=root/'sprint3'
out=root/'docs/sprint4'
# Extract only the pure rolling/score rules; do not import application or Qiskit modules.
code=(src/'common.py').read_text(encoding='utf-8')
names={'maintenance_score','maintenance_class_from_score','add_rolling_features'}
nodes=[n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name in names]
env={'np':np,'W_ROLL':20}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'common.py:rules-only','exec'),env)
df=pd.read_csv(src/'sprint2_core/dataset_motor_sprint2_bruto.csv')
rolled=env['add_rolling_features'](df)
classes=['normal','monitoramento','alerta','critico']
oper=rolled[rolled.classe_manutencao.isin(classes)].copy()
scores=[env['maintenance_score'](*row) for row in oper[['vib_roll','harm_roll','efic_roll','efic_slope']].itertuples(index=False,name=None)]
pred=[env['maintenance_class_from_score'](v) for v in scores]
ok=np.array(pred)==oper.classe_manutencao.to_numpy()
result={'version':'1.5','consolidation_date':'2026-11-03','scope':'Conferência documental da regra existente; sem treino, inferência de modelos ou benchmark da API.','rule_source':'sprint3/common.py: maintenance_score, maintenance_class_from_score, add_rolling_features','population':'Todas as linhas de classes operacionais, após calcular janelas causais na sequência completa do CSV.','window':20,'thresholds':[0.3,0.8,1.5],'rows':len(oper),'matches':int(ok.sum()),'mismatches':int((~ok).sum()),'agreement':float(ok.mean()),'mismatch_rows':[],'versions':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__},'source_sha256':{str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src/'common.py',src/'train_and_persist.py',src/'sprint2_core/dataset_motor_sprint2_bruto.csv']}}
for j in np.flatnonzero(~ok):
    row=oper.iloc[j]
    result['mismatch_rows'].append({'csv_data_index_zero_based':int(oper.index[j]),'csv_line_including_header':int(oper.index[j])+2,'timestamp':row.timestamp,'label':row.classe_manutencao,'recomputed':pred[j],'score':scores[j]})
baseline_path=out/'baseline_majoritaria_manutencao.json'
baseline=json.loads(baseline_path.read_text(encoding='utf-8'))
for name,expected in baseline['source_sha256'].items():
    assert hashlib.sha256((src/name).read_bytes()).hexdigest()==expected, name
indices=baseline['test_csv_data_indices_zero_based']
assert len(indices)==baseline['n_test']==len(set(indices))==988
assert set(indices).issubset(set(oper.index))
positions=oper.index.get_indexer(indices)
actual=oper.classe_manutencao.to_numpy()[positions]
predicted=np.asarray(pred)[positions]
matrix=[[int(((actual==a)&(predicted==b)).sum()) for b in classes] for a in classes]
f1=[]
for i in range(len(classes)):
    denominator=sum(matrix[i])+sum(row[i] for row in matrix)
    f1.append(2*matrix[i][i]/denominator if denominator else 0.0)
holdout_ok=actual==predicted
result['version']='1.5'
result['reconstructed_holdout']={'index_source':baseline_path.name,'index_source_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),'method':'Seleção exata dos índices registrados pela baseline; variáveis rolantes calculadas na sequência completa antes da seleção. Sem ajustar pesos ou limiares no teste.','n':len(indices),'matches':int(holdout_ok.sum()),'mismatches':int((~holdout_ok).sum()),'agreement':float(holdout_ok.mean()),'f1_macro':float(np.mean(f1)),'f1_per_class':dict(zip(classes,f1)),'class_order':classes,'confusion_matrix':matrix,'test_csv_data_indices_zero_based':indices,'mismatch_rows':[row for row in result['mismatch_rows'] if row['csv_data_index_zero_based'] in set(indices)],'limitation':baseline['split']}
(out/'conferencia_regra_manutencao.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True,indent=2))
