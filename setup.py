from setuptools import setup, find_packages

setup(
    name='HyperPapers',
    version='0.1.0',
    packages=["main.py","system_interface.py"],
    install_requires=[
        'GPUtil',
        'PyQt6',
        'watchdog',
    ],
    entry_points={
        'console_scripts': [
            'my-script=HyperPapers.main:main',
        ],
    },
)