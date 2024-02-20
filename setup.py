# # -*- coding: utf-8 -*-
# from setuptools import setup, find_packages

# long_description = open("README.md").read()

# with open("requirements.txt", mode='r') as f:
#     install_requires = f.read().split('\n')

# install_requires = [e for e in install_requires if len(e) > 0]

# d = {}
# exec(open("expipe_plugin_cinpla/version.py").read(), None, d)
# version = d['version']
# pkg_name = "expipe-pligin-cinpla"

# setup(
#     name=pkg_name,
#     packages=find_packages(),
#     version=version,
#     include_package_data=True,
#     author="CINPLA",
#     author_email="",
#     maintainer="Mikkel Elle Lepperød, Alessio Buccino",
#     maintainer_email="mikkel@simula.no",
#     platforms=["Linux", "Windows"],
#     description="Expipe plugins for the CINPLA lab",
#     url="https://github.com/CINPLA/expipe-plugin-cinpla",
#     long_description_content_type="text/markdown",
#     install_requires=install_requires,
#     long_description=long_description,
#     classifiers=['Intended Audience :: Science/Research',
#                  'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
#                  'Natural Language :: English',
#                  'Programming Language :: Python :: 3',
#                  'Topic :: Scientific/Engineering'],
#     python_requires='>=3.9',
# )

import setuptools


if __name__ == "__main__":
    setuptools.setup()
