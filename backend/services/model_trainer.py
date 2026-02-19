"""
模型训练服务
从 SQLite 加载数据，训练 sklearn 模型并导出 CoreML
"""
import numpy as np
from typing import Optional
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedShuffleSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import pickle

from sqlalchemy.orm import Session as DBSession

from services import storage
from services.feature_extractor import get_feature_names


def _load_training_data(db: DBSession, session_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """从 SQLite 加载训练数据"""
    actions = storage.get_training_actions(db, session_ids)

    if not actions:
        raise ValueError("没有找到可用的训练数据。请确保至少有一个 session 包含标注数据。")

    all_features = []
    all_labels = []

    for a in actions:
        features = a.get("features")
        if not features or len(features) < 5:
            continue
        all_features.append(features)
        all_labels.append(a["manual_quality"])

    if not all_features:
        raise ValueError("没有找到带特征的训练数据。")

    X = np.array(all_features, dtype=np.float64)
    y = np.array(all_labels)

    X = np.nan_to_num(X, nan=0.0)

    return X, y


def run_training(
    db: DBSession,
    run_id: str,
    session_ids: list[str],
    model_type: str = "svm",
    svm_c: float = 1.0,
    svm_kernel: str = "rbf",
    max_depth: Optional[int] = None,
    n_estimators: int = 100,
) -> dict:
    """执行训练，使用 train/test split"""

    X, y = _load_training_data(db, session_ids)

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # 创建模型
    if model_type == "svm":
        model = SVC(C=svm_c, kernel=svm_kernel, probability=True)
    elif model_type == "decision_tree":
        model = DecisionTreeClassifier(max_depth=max_depth)
    elif model_type == "random_forest":
        model = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")

    # 交叉验证
    cv_folds = min(5, len(X))
    if cv_folds >= 2:
        cv_scores = cross_val_score(model, X, y_encoded, cv=cv_folds, scoring='accuracy')
    else:
        cv_scores = np.array([0.0])

    # Train/Test split (80/20)
    if len(X) >= 10:
        sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(sss.split(X, y_encoded))
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y_encoded[train_idx], y_encoded[test_idx]
    else:
        X_train, X_test = X, X
        y_train, y_test = y_encoded, y_encoded

    # 训练
    model.fit(X_train, y_train)

    # 在 test set 上评估
    y_pred = model.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, average='weighted', zero_division=0))
    rec = float(recall_score(y_test, y_pred, average='weighted', zero_division=0))
    f1 = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
    cm = confusion_matrix(y_test, y_pred).tolist()

    # 用全量数据重新训练最终模型（用于导出）
    model.fit(X, y_encoded)

    # 保存 sklearn 模型 (pickle)
    pkl_path = storage.get_model_path(run_id, ext=".pkl")
    with open(pkl_path, 'wb') as f:
        pickle.dump({"model": model, "label_encoder": le, "feature_count": X.shape[1]}, f)

    # 尝试导出 CoreML
    coreml_exported = False
    try:
        import coremltools as ct
        coreml_model = ct.converters.sklearn.convert(
            model,
            input_features=get_feature_names()[:X.shape[1]],
            output_feature_names="quality"
        )
        coreml_path = storage.get_model_path(run_id, ext=".mlmodel")
        coreml_model.save(str(coreml_path))
        coreml_exported = True
    except Exception as e:
        print(f"[Trainer] CoreML export failed: {e}")

    # 保存训练记录到 SQLite
    result = {
        "run_id": run_id,
        "status": "completed",
        "model_type": model_type,
        "session_ids": session_ids,
        "sample_count": len(X),
        "good_count": int(np.sum(y == 'good')),
        "bad_count": int(np.sum(y == 'bad')),
        "feature_count": X.shape[1],
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1_score": f1,
        "cv_mean": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "confusion_matrix": cm,
        "labels": le.classes_.tolist(),
        "coreml_exported": coreml_exported,
        "hyperparams": {
            "model_type": model_type,
            "svm_c": svm_c,
            "svm_kernel": svm_kernel,
            "max_depth": max_depth,
            "n_estimators": n_estimators,
        }
    }
    storage.save_training_run(db, run_id, result)

    return result
