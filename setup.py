import setuptools

if __name__ == "__main__":
    setuptools.setup(
        name="protobloop",
        version="0.1.0",
        url="https://github.com/numberoverzero/protobloop",
        package_dir={"": "src"},
        packages = setuptools.find_packages(where="src"),
        install_requires=["bloop"],
    )
