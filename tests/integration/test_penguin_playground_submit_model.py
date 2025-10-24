import os
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from aimodelshare.playground import ModelPlayground
from aimodelshare.aws import set_credentials

@pytest.mark.integration
def test_penguin_playground_submit_model_all():
    required_env = ["USERNAME", "PASSWORD", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]
    missing = [k for k in required_env if not os.environ.get(k)]
    if missing:
        pytest.skip(f"Missing required environment variables for integration test: {missing}")

    try:
        import seaborn as sns
    except ImportError:
        pytest.skip("seaborn not installed")

    penguins = sns.load_dataset("penguins").dropna()
    if penguins.empty:
        pytest.skip("Penguins dataset unexpectedly empty")

    X = penguins[['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']]
    y = penguins['sex']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    numeric_features = X.columns.tolist()
    numeric_transformer = Pipeline(steps=[('scaler', StandardScaler())])
    preprocess = ColumnTransformer([('num', numeric_transformer, numeric_features)])
    preprocess.fit(X_train)

    def preprocessor(df):
        return preprocess.transform(df)

    model = LogisticRegression(max_iter=300)
    model.fit(preprocessor(X_train), y_train)
    prediction_labels = model.predict(preprocessor(X_test))
    y_test_labels = list(y_test)

    myplayground = ModelPlayground(input_type="tabular", task_type="classification", private=True)

    try:
        myplayground.create(eval_data=y_test_labels)
    except Exception as e:
        pytest.skip(f"Playground creation failed due to environment/network: {e}")

    try:
        apiurl = myplayground.playground_url
        set_credentials(apiurl=apiurl)
    except Exception as e:
        pytest.skip(f"set_credentials failed: {e}")

    try:
        myplayground.submit_model(model=model,
                                   preprocessor=preprocessor,
                                   prediction_submission=prediction_labels,
                                   submission_type="all",
                                   input_dict={"description": "Penguin integration test model", "tags": "integration-penguin"},
                                   onnx_timeout=60)
    except Exception as e:
        pytest.fail(f"submit_model raised an exception: {e}")

    assert hasattr(myplayground, "model_page"), "model_page attribute missing after submission."
    assert isinstance(myplayground.model_page, str) and len(myplayground.model_page) > 0, "model_page not populated."
    assert "modelshare.ai/detail/model:" in myplayground.model_page, "model_page format unexpected."
