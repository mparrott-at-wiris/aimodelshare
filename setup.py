
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='aimodelshare',
    version='0.1.58',  # Updated version for pydot dependency and ONNX graph rendering support
    author="Michael Parrott",
    author_email="mikedparrott@modelshare.org",
    description="Deploy locally saved machine learning models to a live rest API and web-dashboard.  Share it with the world via modelshare.org",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://www.modelshare.org",
    packages=setuptools.find_packages(),
    # Core dependencies required for aimodelshare functionality
    install_requires=[
        'numpy>=1.22.0',   # Array and numerical computing
        'pandas',          # Data manipulation and analysis
        'requests',        # HTTP library for API calls
        'boto3',           # AWS SDK for cloud storage
        'onnx',            # ONNX model format support
        'onnxmltools',     # ONNX conversion tools
        'onnxruntime',     # ONNX runtime for model inference
        'skl2onnx',        # Scikit-learn to ONNX conversion
        'tf2onnx',         # TensorFlow to ONNX conversion
        'scikit-learn',    # Machine learning library
        'scikeras',        # Keras wrapper for scikit-learn
        'shortuuid',       # Short UUID generation
        'Pympler',         # Memory profiling
        'wget',            # File download utility
        'PyJWT<2.0',       # JSON Web Token library (version constraint for compatibility)
        'pydot',           # ONNX graph visualization support (required by onnx.tools.net_drawer)
        'regex',   

    ],
    extras_require={
        'visual': ['pydot', 'graphviz'],  # Optional dependencies for full ONNX graph rendering
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",  # Proprietary license (not OSI approved)
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
    include_package_data=True,
    #package_data={'': ['placeholders/model.onnx', 'placeholders/preprocessor.zip']},
    )     
  
