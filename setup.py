import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="dwrap",
    version="0.0.1",
    author="Henry Choi",
    author_email="henrychoi327@gmail.com",
    description="A Customized Wrapper of Dart Open Api",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/choiHenry/dwrap",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)