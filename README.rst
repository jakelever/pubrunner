=========
PubRunner
=========

|pypi| |build-status| |coverage| |docs| |license|

.. |pypi| image:: https://img.shields.io/pypi/v/pubrunner.svg
   :target: https://pypi.python.org/pypi/pubrunner
   :alt: PyPI Release

.. |build-status| image:: https://travis-ci.org/jakelever/pubrunner.svg?branch=master
   :target: https://travis-ci.org/jakelever/pubrunner
   :alt: Travis CI status

.. |coverage| image:: https://coveralls.io/repos/github/jakelever/pubrunner/badge.svg?branch=master
   :target: https://coveralls.io/github/jakelever/pubrunner?branch=master
   :alt: Coverage status
   
.. |docs| image:: https://readthedocs.org/projects/pubrunner/badge/?version=latest
   :target: http://pubrunner.readthedocs.io/en/latest/
   :alt: Documentation status
   
.. |license| image:: https://img.shields.io/badge/License-MIT-blue.svg
   :target: https://opensource.org/licenses/MIT
   :alt: MIT license

PubRunner is a framework to keep text mining tools running on the latest publications.

Installation
------------

PubRunner uses Python3 and can be installed via `pip`_ from `PyPI`_::

   $ pip install pubrunner

Usage
-----

To run Pubrunner, you just need to provide it with a path to a biomedical text mining tool (e.g. a Github repo or a local directory). The flag --test tells Pubrunner to execute the test set. Omitting that gets Pubrunner to run the tool on the full corpus (which for Ab3P is PubMed).::

   $ pubrunner --test https://github.com/jakelever/Ab3P

Is PubRunner for me?
--------------------

Are you a biomedical text mining tool developer? Then likely yes. PubRunner makes it easy to run a text mining tool across PubMed and keep it working!

Examples
--------

Check out the `examples directory`_ to see a small number of projects that use PubRunner on Pubmed.

Contributing
------------
Contributions are very welcome.

License
-------

Distributed under the terms of the `MIT`_ license, "pubrunner" is free and open source software

Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`MIT`: http://opensource.org/licenses/MIT
.. _`file an issue`: https://github.com/jakelever/pubrunner/issues
.. _`pip`: https://pypi.python.org/pypi/pip/
.. _`PyPI`: https://pypi.python.org/pypi
.. _`examples directory`: https://github.com/jakelever/pubrunner/tree/master/examples

