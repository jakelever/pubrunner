Welcome to PubRunner documentation!
===================================

.. currentmodule:: pubrunner

.. toctree::
   :maxdepth: 2
   :hidden:

   Home <self>
   tutorial

Overview
--------

PubRunner solves the problem of regularly running and testing a text mining tool. It is primarily designed for biomedical text mining tools that use Pubmed or Pubmed Central. It follows the four steps outlined below.

1. Fetch the latest version of the corpus to be mined (such as PubMed or PMC) and any additional corpora/resources needed
2. Intelligently execute the text mining tool using the corpora
3. Upload the output of the text mining tool to an appropriate location (e.g. FTP or Zenodo)
4. Update the PubRunner website with the location of the latest output and code

Installation
------------

PubRunner can be installed using pip and requires Python 3.

.. code-block:: bash

   pip install pubrunner

Running PubRunner
-----------------

To run PubRunner, use the terminal command 'pubrunner'. The main argument should be the location of the text mining tool. This can be a local directory or Github repo. The command will attempt to run the test example of the Bio2Vec project.

.. code-block:: bash

   pubrunner --test https://github.com/jakelever/Ab3P

To run the full example, omit the "--test" flag. Important: depending on the project, this may required downloading the entirety of PubMed (~180GB). It is recommended to use a cluster for large projects like this.

Getting Started
---------------

A first place to start would be the :doc:`tutorial` page. Then you could check out the `example projects`_ to see a few different use cases. And check out the `Ab3P project` that scans for abbreviations across PubMed and PubMed Central.

If you have any questions, ideas, bugs, please create an `issue`_.

.. _`example projects`: https://github.com/jakelever/pubrunner/tree/master/examples
.. _`Ab3P project`: https://github.com/jakelever/Ab3P
.. _`issue`: https://github.com/jakelever/pubrunner/issues

