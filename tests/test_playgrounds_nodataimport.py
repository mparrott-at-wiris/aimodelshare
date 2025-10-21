from aimodelshare.playground import ModelPlayground, Experiment, Competition
from aimodelshare.aws import set_credentials, get_aws_token
import aimodelshare as ai
from aimodelshare.data_sharing.utils import redo_with_write

from unittest.mock import patch

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split # Added this import
import seaborn as sns # Added this import

import pandas as pd
import shutil
import os



def test_configure_credentials():

	# when testing locally, we can set credentials from file
	try:
		set_credentials(credential_file="../../../credentials.txt", type="deploy_model")
	except Exception as e:
		print(e)

	try:
		set_credentials(credential_file="../../credentials.txt", type="deploy_model")
	except Exception as e:
		print(e)

	# mock user input
	inputs = [os.environ.get('USERNAME'),
			  os.environ.get('PASSWORD'),
			  os.environ.get('AWS_ACCESS_KEY_ID'),
			  os.environ.get('AWS_SECRET_ACCESS_KEY'),
			  os.environ.get('AWS_REGION')]


	with patch("getpass.getpass", side_effect=inputs):
		from aimodelshare.aws import configure_credentials
		configure_credentials()

	# clean up credentials file
	os.remove("credentials.txt")


def test_playground_penguins():

	# when testing locally, we can set credentials from file
	try:
		set_credentials(credential_file="../../../credentials.txt", type="deploy_model")
	except Exception as e:
		print(e)

	try:
		set_credentials(credential_file="../../credentials.txt", type="deploy_model")
	except Exception as e:
		print(e)

	# mock user input
	inputs = [os.environ.get('USERNAME'),
			  os.environ.get('PASSWORD'),
			  os.environ.get('AWS_ACCESS_KEY_ID'),
			  os.environ.get('AWS_SECRET_ACCESS_KEY'),
			  os.environ.get('AWS_REGION')]

	with patch("getpass.getpass", side_effect=inputs):
		from aimodelshare.aws import configure_credentials
		configure_credentials()

	# set credentials
	set_credentials(credential_file="credentials.txt", type="deploy_model")

	# clean up credentials file
	os.remove("credentials.txt")

	# Step 4: Load and prepare evaluation data (penguin sex labels)
	penguins = sns.load_dataset("penguins").dropna()
	X = penguins[['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']]
	y = penguins['sex']

	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

	# Prepare evaluation data used in class leaderboard (List of y_test values)
	y_test_labels = list(y_test)
	example_data = X_test.copy() # for deployment

	# Create a simple preprocessor for the numeric data
	numeric_features = ['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']
	numeric_transformer = Pipeline(steps=[
	    ('scaler', StandardScaler())])

	preprocess = ColumnTransformer(
	    transformers=[
	        ('num', numeric_transformer, numeric_features)])

	# fit preprocessor to your data
	preprocess = preprocess.fit(X_train)

	# Write function to transform data with preprocessor
	def preprocessor(data):
	    preprocessed_data=preprocess.transform(data)
	    return preprocessed_data

	# build a simple model
	model = LogisticRegression()
	model.fit(preprocessor(X_train), y_train)

	# generate predictions
	prediction_labels = model.predict(preprocessor(X_test))

	# Step 5: Create your Model Playground!
	myplayground=ModelPlayground(input_type="tabular",
	                             task_type="classification",
	                             private=True) # Using private=True for testing

	myplayground.create(eval_data=y_test_labels)

	# Submit Model to Experiment Leaderboard
	myplayground.submit_model(model = model,
							  preprocessor=preprocessor,
							  prediction_submission=prediction_labels,
							  input_dict={"description": "Penguin test model", "tags": "pytest-penguin"},
							  submission_type="all")

	# Check Competition Leaderboard
	data = myplayground.get_leaderboard()
	myplayground.stylize_leaderboard(data)
	assert isinstance(data, pd.DataFrame)

	# deploy model
	myplayground.deploy_model(model_version=1, example_data=example_data, y_train=y_train)

	# delete
	myplayground.delete_deployment(confirmation=False)

	# No local cleanup needed as seaborn.load_dataset() doesn't create files/dirs
