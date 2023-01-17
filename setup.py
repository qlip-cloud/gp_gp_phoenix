from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in gp_phonix_integration/__init__.py
from gp_phonix_integration import __version__ as version

setup(
	name='gp_phonix_integration',
	version=version,
	description='Integration Phonix',
	author='Rafael Licett',
	author_email='rafael.licett@mentum.group',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
