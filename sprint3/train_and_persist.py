"""
Sprint 3, Fase 1: treino e persistencia de todos os modelos do Digital Twin.

Treina (reusando o pipeline do Sprint 2) e salva em models/:

Cenario 1, deteccao de anomalias:
  - 4 baselines clássicos pontuais (SVM-RBF, RF, MLP, GB) sobre 9 sensores
    → preproc pontual (MinMaxScaler[-π,π] → PCA(4) → MinMaxScaler[-π,π]) + clf
  - QSVC + Amplitude Encoding (2 qubits) sobre janelas 10×9 (pipeline Sprint 2)
    + Platt scaling para converter decision_function em probabilidade

Cenario 2, predicao de manutencao (multiclasse, 4 classes operacionais):
  - Random Forest multiclasse (clássico)
  - VQC (PauliFeatureMap + EfficientSU2 + SPSA). So os pesos sao persistidos;
    a QNN é reconstruída deterministicamente na inferência (common.build_maintenance_qnn)

Também salva: defaults de imputação (medianas da operação normal),
metrics.json (holdout 80/20) e recursos quânticos (qubits/depth) p/ o roadmap.

Uso:  python train_and_persist.py [--fast]   (--fast reduz o VQC p/ smoke test)
"""

import json
import sys
import time
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVC

from common import (
    BRUTO_CSV,
    MAINT_FEATURES,
    ROLLING_FEATURES,
    MAINTENANCE_CLASSES,
    MODELS_DIR,
    SENSOR_COLS,
    SPRINT2_DIR,
    WINDOW_SIZE,
    WINDOW_STEP,
    add_rolling_features,
    build_amplitude_feature_map,
    build_maintenance_qnn,
    build_windows_from_bruto,
    clip_to_pi,
    make_hybrid_pipeline,
)

SEED = 42
np.random.seed(SEED)
FAST = "--fast" in sys.argv


def log(msg):
    print(msg, flush=True)


def batch_latency_ms(predict_fn, X, repeat=3):
    """Latência média por amostra (batch amortizado)."""
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        predict_fn(X)
        best = min(best, time.perf_counter() - t0)
    return best / len(X) * 1000.0


def main():
    MODELS_DIR.mkdir(exist_ok=True)
    metrics = {"cenario1_anomalia": {}, "cenario2_manutencao": {}, "recursos_quanticos": {}}

    log("=" * 70)
    log("SPRINT 3, FASE 1: TREINO E PERSISTENCIA")
    log("=" * 70)

    df = pd.read_csv(BRUTO_CSV)
    X_raw = df[SENSOR_COLS].values
    y_anom = df["label_anomalia"].values

    # ── Defaults de imputação (D1): mediana da operação normal por sensor ──
    normais = df[(df["ciclo_operacao"] == "normal") & (df["label_anomalia"] == 0)]
    imputation = {c: float(normais[c].median()) for c in SENSOR_COLS}
    with open(MODELS_DIR / "imputation_defaults.json", "w", encoding="utf-8") as f:
        json.dump(imputation, f, indent=2, ensure_ascii=False)
    log(f"\n[1/6] Defaults de imputação salvos ({len(imputation)} sensores)")

    # ── Pré-processador pontual (idêntico ao refinamento: fit no bruto inteiro) ──
    preproc = Pipeline([
        ("scaler1", MinMaxScaler(feature_range=(-np.pi, np.pi))),
        ("pca", PCA(n_components=4, random_state=SEED)),
        ("scaler2", MinMaxScaler(feature_range=(-np.pi, np.pi))),
    ])
    X_pca = preproc.fit_transform(X_raw)
    joblib.dump(preproc, MODELS_DIR / "preproc_pontual.joblib")
    var_exp = float(preproc.named_steps["pca"].explained_variance_ratio_.sum())
    log(f"[2/6] Pré-processador pontual salvo (variância PCA: {var_exp * 100:.1f}%)")

    # ════════════════════════════════════════════════════════════════
    # CENARIO 1, classicos pontuais
    # ════════════════════════════════════════════════════════════════
    idx = np.arange(len(df))
    idx_tr, idx_te = train_test_split(
        idx, test_size=0.2, stratify=y_anom, random_state=SEED
    )
    Xtr, Xte = X_pca[idx_tr], X_pca[idx_te]
    ytr, yte = y_anom[idx_tr], y_anom[idx_te]

    # sample_weight p/ GB e MLP (não têm class_weight)
    w_pos = len(ytr) / (2.0 * max((ytr == 1).sum(), 1))
    w_neg = len(ytr) / (2.0 * max((ytr == 0).sum(), 1))
    sw = np.where(ytr == 1, w_pos, w_neg)

    classicos = {
        "svm_rbf": SVC(kernel="rbf", gamma="scale", class_weight="balanced",
                       probability=True, random_state=SEED),
        "random_forest": RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                                random_state=SEED, n_jobs=-1),
        "mlp": MLPClassifier(hidden_layer_sizes=(64, 32), activation="relu",
                             solver="adam", max_iter=400, random_state=SEED),
        "gradient_boosting": GradientBoostingClassifier(n_estimators=100, random_state=SEED),
    }

    log("\n[3/6] Cenario 1, baselines classicos (holdout 80/20):")
    for name, clf in classicos.items():
        t0 = time.perf_counter()
        if name == "gradient_boosting":
            clf.fit(Xtr, ytr, sample_weight=sw)
        else:
            clf.fit(Xtr, ytr)
        fit_s = time.perf_counter() - t0

        proba = clf.predict_proba(Xte)[:, 1]
        pred = clf.predict(Xte)
        m = {
            "auc": round(float(roc_auc_score(yte, proba)), 4),
            "f1_anomalia": round(float(f1_score(yte, pred, zero_division=0)), 4),
            "accuracy": round(float(accuracy_score(yte, pred)), 4),
            "fit_s": round(fit_s, 3),
            "latencia_ms_amostra": round(batch_latency_ms(clf.predict, Xte), 4),
            "n_treino": int(len(ytr)),
        }
        metrics["cenario1_anomalia"][name] = m
        joblib.dump(clf, MODELS_DIR / f"anomalia_{name}.joblib")
        log(f"   {name:<18} AUC={m['auc']:.3f}  F1={m['f1_anomalia']:.3f}  "
            f"acc={m['accuracy']:.3f}  fit={fit_s:.2f}s  {m['latencia_ms_amostra']:.3f} ms/amostra")

    # ════════════════════════════════════════════════════════════════
    # CENARIO 1, QSVC + Amplitude Encoding (janelado, pipeline Sprint 2)
    # ════════════════════════════════════════════════════════════════
    log("\n[4/6] Cenario 1, QSVC + Amplitude Encoding (janelas 10x9):")
    X_win, y_win = build_windows_from_bruto(
        str(BRUTO_CSV), window_size=WINDOW_SIZE, step=WINDOW_STEP, label_mode="any"
    )
    Wtr, Wte, ywtr, ywte = train_test_split(
        X_win, y_win, test_size=0.2, stratify=y_win, random_state=SEED
    )
    # Platt: separa 20% do treino p/ calibrar decision_function → probabilidade
    Wfit, Wcal, yfit, ycal = train_test_split(
        Wtr, ywtr, test_size=0.2, stratify=ywtr, random_state=SEED
    )

    qsvc_pipe = make_hybrid_pipeline(
        build_amplitude_feature_map(4), n_pca=4, amplitude_encoding=True
    )
    t0 = time.perf_counter()
    qsvc_pipe.fit(Wfit, yfit)
    qsvc_fit_s = time.perf_counter() - t0

    platt = LogisticRegression()
    platt.fit(qsvc_pipe.decision_function(Wcal).reshape(-1, 1), ycal)

    scores_te = qsvc_pipe.decision_function(Wte)
    pred_te = qsvc_pipe.predict(Wte)
    fmap = build_amplitude_feature_map(4)
    from arquitetura_hibrida_sprint2 import basis_depth, safe_native_depth

    mq = {
        "auc": round(float(roc_auc_score(ywte, scores_te)), 4),
        "f1_anomalia": round(float(f1_score(ywte, pred_te, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(ywte, pred_te)), 4),
        "fit_s": round(qsvc_fit_s, 3),
        "latencia_ms_amostra": round(batch_latency_ms(qsvc_pipe.predict, Wte, repeat=1), 4),
        "n_treino": int(len(yfit)),
        "n_janelas_total": int(len(y_win)),
    }
    metrics["cenario1_anomalia"]["qsvc_amplitude"] = mq
    metrics["recursos_quanticos"]["qsvc_amplitude"] = {
        "n_qubits": int(fmap.num_qubits),
        "depth_native": safe_native_depth(fmap),
        "depth_basis_ucx": basis_depth(fmap),
        "kernel": "FidelityStatevectorKernel (simulador statevector exato)",
    }
    log(f"   qsvc_amplitude     AUC={mq['auc']:.3f}  F1={mq['f1_anomalia']:.3f}  "
        f"acc={mq['accuracy']:.3f}  fit={qsvc_fit_s:.2f}s  {mq['latencia_ms_amostra']:.3f} ms/amostra")

    # Persistência: joblib do pipeline inteiro; fallback = dados de treino p/ re-fit no boot
    bundle = {"pipeline": qsvc_pipe, "platt": platt}
    try:
        joblib.dump(bundle, MODELS_DIR / "anomalia_qsvc_amplitude.joblib")
        joblib.load(MODELS_DIR / "anomalia_qsvc_amplitude.joblib")["pipeline"].predict(Wte[:2])
        log("   pipeline QSVC serializado e round-trip validado (joblib)")
    except Exception as exc:  # pragma: no cover
        log(f"   AVISO: joblib do QSVC falhou ({exc}); salvando dados p/ re-fit no boot")
        np.savez(MODELS_DIR / "anomalia_qsvc_refit.npz", X=Wfit, y=yfit)
        joblib.dump({"platt": platt}, MODELS_DIR / "anomalia_qsvc_platt.joblib")

    # ════════════════════════════════════════════════════════════════
    # CENARIO 2, manutencao multiclasse (classico RF + VQC quantico)
    # ════════════════════════════════════════════════════════════════
    log("\n[5/6] Cenario 2, predicao de manutencao (4 classes operacionais):")
    # Features rolantes calculadas sobre a série COMPLETA em ordem temporal
    # (como no refinamento), depois filtra as linhas operacionais.
    df_roll = add_rolling_features(df)
    oper = df_roll[df_roll["classe_manutencao"].isin(MAINTENANCE_CLASSES)]
    Xm = oper[MAINT_FEATURES].values
    ym = oper["classe_manutencao"].map(
        {c: i for i, c in enumerate(MAINTENANCE_CLASSES)}
    ).values

    Xmtr, Xmte, ymtr, ymte = train_test_split(
        Xm, ym, test_size=0.2, stratify=ym, random_state=SEED
    )
    dist = {MAINTENANCE_CLASSES[i]: int(c) for i, c in enumerate(np.bincount(ym))}
    log(f"   distribuição: {dist}  ({len(MAINT_FEATURES)} features: 9 sensores + 4 rolantes)")

    rf_man = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                    random_state=SEED, n_jobs=-1)
    t0 = time.perf_counter()
    rf_man.fit(Xmtr, ymtr)
    rf_fit_s = time.perf_counter() - t0
    pred_m = rf_man.predict(Xmte)
    mm = {
        "accuracy": round(float(accuracy_score(ymte, pred_m)), 4),
        "f1_macro": round(float(f1_score(ymte, pred_m, average="macro", zero_division=0)), 4),
        "f1_por_classe": {
            MAINTENANCE_CLASSES[i]: round(float(v), 4)
            for i, v in enumerate(f1_score(ymte, pred_m, average=None, zero_division=0,
                                           labels=range(len(MAINTENANCE_CLASSES))))
        },
        "fit_s": round(rf_fit_s, 3),
        "latencia_ms_amostra": round(batch_latency_ms(rf_man.predict, Xmte), 4),
        "n_treino": int(len(ymtr)),
    }
    metrics["cenario2_manutencao"]["random_forest"] = mm
    joblib.dump(rf_man, MODELS_DIR / "manutencao_random_forest.joblib")
    log(f"   random_forest      acc={mm['accuracy']:.3f}  F1-macro={mm['f1_macro']:.3f}  "
        f"fit={rf_fit_s:.2f}s")

    # ── VQC ──────────────────────────────────────────────────────────
    # Entrada do VQC: as 4 features ROLANTES de degradação direto (mesmo espaço
    # em que o rotulo foi definido no Sprint 2), escaladas para [-pi,pi], sem PCA.
    # PCA(4) sobre as 13 features diluía o sinal (acc ≈ aleatório no piloto).
    preproc_man = MinMaxScaler(feature_range=(-np.pi, np.pi))
    Xmtr_q = preproc_man.fit_transform(Xmtr[:, -len(ROLLING_FEATURES):])
    Xmte_q = preproc_man.transform(Xmte[:, -len(ROLLING_FEATURES):])
    joblib.dump(preproc_man, MODELS_DIR / "preproc_manutencao.joblib")

    n_per_class = 30 if FAST else 100
    maxiter = 15 if FAST else 120
    rng = np.random.default_rng(SEED)
    sel = np.concatenate([
        rng.choice(np.where(ymtr == k)[0],
                   size=min(n_per_class, int((ymtr == k).sum())), replace=False)
        for k in range(len(MAINTENANCE_CLASSES))
    ])
    rng.shuffle(sel)
    Xv, yv = clip_to_pi(Xmtr_q[sel]), ymtr[sel]
    log(f"   VQC: subamostra de {len(yv)} ({n_per_class}/classe), SPSA maxiter={maxiter} …")

    from qiskit_machine_learning.algorithms import VQC
    try:
        from qiskit_machine_learning.optimizers import SPSA
    except ImportError:
        from qiskit_algorithms.optimizers import SPSA

    qnn, feature_map, ansatz = build_maintenance_qnn()
    vqc = VQC(
        feature_map=feature_map,
        ansatz=ansatz,
        loss="cross_entropy",
        optimizer=SPSA(maxiter=maxiter),
        # sem output_shape explícito o VQC 0.8 fixa interpret=x%2 no construtor
        # e o fit so atualiza o output_shape. Classes 2..3 ficariam inalcancaveis
        output_shape=len(MAINTENANCE_CLASSES),
    )
    y_onehot = np.eye(len(MAINTENANCE_CLASSES))[yv]
    t0 = time.perf_counter()
    vqc.fit(Xv, y_onehot)
    vqc_fit_s = time.perf_counter() - t0

    weights = np.asarray(vqc.weights, dtype=float)
    np.savez(MODELS_DIR / "manutencao_vqc.npz",
             weights=weights, classes=np.array(MAINTENANCE_CLASSES))

    # Consistência: a QNN reconstruída (caminho da inferência) tem de reproduzir
    # as predicoes do VQC treinado. Senao os pesos persistidos sao inuteis.
    check = clip_to_pi(Xmte_q[:20])
    pred_vqc = np.argmax(vqc.predict(check), axis=1)
    pred_qnn = np.argmax(qnn.forward(check, weights), axis=1)
    agree = float(np.mean(pred_vqc == pred_qnn))
    log(f"   consistência VQC × QNN reconstruída: {agree * 100:.0f}% "
        f"({'OK' if agree == 1.0 else 'DIVERGENCIA, investigar interpret/ordem de params'})")

    # Avaliação no holdout via QNN reconstruída (mesmo caminho da inferência)
    probs_te = qnn.forward(clip_to_pi(Xmte_q), weights)
    pred_v = np.argmax(probs_te, axis=1)
    from qiskit import transpile

    circ = qnn.circuit
    bound = circ.assign_parameters(np.ones(circ.num_parameters) / np.sqrt(circ.num_parameters))
    depth_ucx = int(transpile(bound, basis_gates=["u", "cx"], optimization_level=0).depth())
    mv = {
        "accuracy": round(float(accuracy_score(ymte, pred_v)), 4),
        "f1_macro": round(float(f1_score(ymte, pred_v, average="macro", zero_division=0)), 4),
        "fit_s": round(vqc_fit_s, 3),
        "latencia_ms_amostra": round(
            batch_latency_ms(lambda X: qnn.forward(X, weights), clip_to_pi(Xmte_q[:200]), repeat=1), 4),
        "n_treino": int(len(yv)),
        "spsa_maxiter": maxiter,
    }
    metrics["cenario2_manutencao"]["vqc"] = mv
    metrics["recursos_quanticos"]["vqc"] = {
        "n_qubits": 4,
        "feature_map": "PauliFeatureMap(reps=1, paulis=[Z, ZZ])",
        "ansatz": "EfficientSU2(reps=2)",
        "n_parametros_treinaveis": int(len(weights)),
        "depth_basis_ucx": depth_ucx,
        "otimizador": f"SPSA(maxiter={maxiter})",
    }
    log(f"   vqc                acc={mv['accuracy']:.3f}  F1-macro={mv['f1_macro']:.3f}  "
        f"fit={vqc_fit_s:.1f}s  ({len(weights)} parâmetros, depth {depth_ucx})")

    # ════════════════════════════════════════════════════════════════
    log("\n[6/6] Salvando metrics.json …")
    with open(MODELS_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    log("\n✅ Artefatos em models/: " + ", ".join(
        sorted(p.name for p in MODELS_DIR.iterdir())))


if __name__ == "__main__":
    main()
