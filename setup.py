"""HubLabBot.

This setup.py is made for the Nix package manager.
See version and dependencies in ./tools/cfg/nix/default.nix in this repo.
"""
from distutils.core import setup


PKG_DIR = 'hublabbot'


setup(
	name=PKG_DIR,
	version='UNKNOWN_VERSION',
	packages=[
		PKG_DIR,
		PKG_DIR + '.github',
		PKG_DIR + '.gitlab',
		PKG_DIR + '.view'],
	package_data={PKG_DIR: [
		'assets/favicon.png',
		'assets/index.templ.html',
		'assets/gitlabci_fail.templ.md']},
	entry_points={
		'console_scripts': [f'hublabbot={PKG_DIR}.main:main']},
	zip_safe=False)
