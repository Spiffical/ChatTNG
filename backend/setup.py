from setuptools import setup, find_packages

setup(
    name="chattng",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "alembic",
        "redis",
        "chromadb",
        "openai",
        "google-generativeai",
        "pyyaml",
    ],
) 