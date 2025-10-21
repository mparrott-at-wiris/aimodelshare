
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='aimodelshare', #TODO:update
    version='0.1.56',        #TODO:update
    author="Michael Parrott",
    author_email="mikedparrott@modelshare.org",
    description="Deploy locally saved machine learning models to a live rest API and web-dashboard.  Share it with the world via modelshare.org",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://www.modelshare.org",
    packages=setuptools.find_packages(),
    install_requires=[
        'boto3',
        'onnx',
        'scikeras',
        'shortuuid',
        'tf2onnx',
        'skl2onnx',
        'onnxruntime',
        'Pympler',
        'wget',
        'onnxmltools'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Proprietary",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    include_package_data=True,
    #package_data={'': ['placeholders/model.onnx', 'placeholders/preprocessor.zip']},
    )     
  
