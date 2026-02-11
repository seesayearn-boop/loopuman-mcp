from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="loopuman",
    version="1.0.0",
    description="The Human API for AI - Give your AI agents instant access to humans",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Loopuman",
    author_email="support@loopuman.com",
    url="https://loopuman.com",
    packages=find_packages(),
    install_requires=["requests>=2.25.0"],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="ai human-in-the-loop microtasks langchain agents",
)
