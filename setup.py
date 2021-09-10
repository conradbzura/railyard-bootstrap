import setuptools


setuptools.setup(
    author="Conrad Bzura",
    author_email="conradbzura@gmail.com",
    entry_points={
        "railyard.bootstrap.version.plugins": [
            "git=railyard.bootstrap.version._git"
        ],
    },
    include_package_data=True,
    name="railyard-bootstrap",
    packages=[f"railyard.{p}" for p in setuptools.find_packages("./railyard")],
    zip_safe=False,
)
