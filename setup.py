from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="serverless-orch",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Serverless API Orchestration Framework using AWS Lambda, DynamoDB, and CloudWatch",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/serverless-orch",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "boto3>=1.28.0",
        "aws-cdk-lib>=2.94.0",
        "constructs>=10.0.0",
        "pydantic>=2.3.0",
        "python-json-logger>=2.0.7",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "moto>=4.2.5",
            "pytest-mock>=3.11.1",
            "black>=23.7.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "serverless-deploy=scripts.deploy:main",
            "serverless-test=scripts.local_test:main",
        ],
    },
)