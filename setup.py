# python setup.py --dry-run --verbose install
# To build: python setup.py sdist bdist_wheel

from distutils.util import convert_path

from setuptools import find_packages, setup

MAIN_NS = {}
VER_PATH = convert_path("src/pyatmo/version.py")
with open(VER_PATH) as ver_file:
    exec(ver_file.read(), MAIN_NS)  # pylint: disable=exec-used

setup(
    name="pyatmo",
    version=MAIN_NS["__version__"],
    author="Hugo Dupras",
    author_email="jabesq@gmail.com",
    packages=find_packages(exclude=["tests"], where="src"),
    package_dir={"pyatmo": "src/pyatmo"},
    scripts=[],
    data_files=[("", ["LICENSE.txt"])],
    url="https://github.com/jabesq/netatmo-api-python",
    license="MIT",
    description=(
        "Simple API to access Netatmo weather station data from any Python 3 script. "
        "Designed for Home-Assitant (but not only)"
    ),
    long_description=open("README.md").read(),
    install_requires=["requests", "requests_oauthlib", "oauthlib"],
)
