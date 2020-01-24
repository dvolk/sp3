from setuptools import setup
from piezo import __version__

setup(
    name='sp3predict',
    version=__version__,
    author='Philip W Fowler',
    author_email="philip.fowler@ndm.ox.ac.uk",
    description="Antibiotic suscetibility predictions from a VCF file and a TB AMR catalogue.",
    url="https://github.com/philipwfowler/sp3predict",
    package_data={'':['../config/*']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"  ],
    python_requires='>=3.5',
    install_requires=[
        "pandas >= 0.23.1",\
        "gumpy",\
        "piezo",\
        "tqdm",\
        "numpy"
    ],
    license='University of Oxford, see LICENSE.md',
    scripts=['bin/sp3predict.py'],
    zip_safe=False
)
