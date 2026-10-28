from pathlib import Path
import pickle

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def train(base_dir=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent
    df = pd.read_csv(base_dir / 'sorted_file.csv')
    if 'error' in df.columns:
        df = df[df['error'].isna()].drop(columns=['error'])
    df = df.dropna()
    X = df.drop(columns=['filename', 'label'])
    y = df['label']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=1, stratify=y,
    )
    # Fit preprocessing only on each training fold to avoid evaluation leakage.
    pipeline = make_pipeline(StandardScaler(), RandomForestClassifier(random_state=1))
    pipeline.fit(X_train, y_train)
    predicted = pipeline.predict(X_test)
    print('Accuracy:', accuracy_score(y_test, predicted))
    print(classification_report(y_test, predicted))
    print('Cross-validated accuracy:', cross_val_score(pipeline, X, y, cv=5).mean())
    pipeline.fit(X, y)
    scaler, classifier = pipeline.steps[0][1], pipeline.steps[1][1]
    plt.figure(figsize=(10, 6))
    plt.barh(X.columns, classifier.feature_importances_)
    plt.xlabel('Importance')
    plt.title('Feature Importance (Random Forest)')
    plt.tight_layout()
    plt.savefig(base_dir / 'feature_importance.png')
    plt.close()
    for name, artifact in [('model.pkl', classifier), ('scaler.pkl', scaler)]:
        with (base_dir / name).open('wb') as stream:
            pickle.dump(artifact, stream)


if __name__ == '__main__':
    train()
