from setuptools import setup, find_packages

setup(
    name='google-adk',
    version='0.2.0',
    packages=['google.adk'],
    package_dir={'google': 'google'},
    install_requires=[
        'google-cloud-aiplatform',
        'protobuf',
        'grpcio',
    ],
)
