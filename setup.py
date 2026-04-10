from setuptools import find_packages, setup

setup(
    name="raysdk-py",
    version="0.1.0",
    description="Python SDK for RaySearch API.",
    long_description_content_type="text/markdown",
    long_description=open("README.md").read(),
    author="Radiata Labs",
    author_email="jameswjj0416@gmail.com",
    package_data={"raysdk-py": ["py.typed"]},
    url="https://github.com/radiata-labs/raysearch-sdk-py",
    packages=find_packages(),
    install_requires=["httpx", "pydantic", "jsonschema"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache-2.0 License",
        "Typing :: Typed",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)