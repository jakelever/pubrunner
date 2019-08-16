# PubRunner

<p>
<a href="https://pypi.python.org/pypi/pubrunner">
   <img src="https://img.shields.io/pypi/v/pubrunner.svg" />
</a>
<a href="https://travis-ci.org/jakelever/pubrunner">
   <img src="https://travis-ci.org/jakelever/pubrunner.svg?branch=master" />
</a>
<a href="https://coveralls.io/github/jakelever/pubrunner?branch=master">
   <img src="https://coveralls.io/repos/github/jakelever/pubrunner/badge.svg?branch=master" />
</a>
<a href="http://pubrunner.readthedocs.io/en/stable/">
   <img src="https://readthedocs.org/projects/pubrunner/badge/?version=stable" />
</a>
<a href="https://opensource.org/licenses/MIT">
   <img src="https://img.shields.io/badge/License-MIT-blue.svg" />
</a>
</p>

PubRunner is a framework to keep text mining tools running on the latest publications.

## Installation

PubRunner uses Python3 and can be installed via [pip](https://pypi.python.org/pypi/pip/) from [PyPI](https://pypi.python.org/pypi).

```
pip install pubrunner
```

## Usage

To run Pubrunner, you just need to provide it with a path to a biomedical text mining tool (e.g. a Github repo or a local directory). The flag --test tells Pubrunner to execute the test set. Omitting that gets Pubrunner to run the tool on the full corpus (which for Ab3P is PubMed).::

```
pubrunner --test https://github.com/jakelever/Ab3P
```

## Is PubRunner for me?

Are you a biomedical text mining tool developer? Then likely yes. PubRunner makes it easy to run a text mining tool across PubMed and keep it working!

## Examples

Check out the [examples directory](https://github.com/jakelever/pubrunner/tree/master/examples
		) to see a small number of projects that use PubRunner on Pubmed.

## Documentation

Documentation including a tutorial can be found at the [readthedocs](http://pubrunner.readthedocs.io/en/stable/) page.

## Contributing
Contributions are very welcome.

## License

Distributed under the terms of the [MIT](http://opensource.org/licenses/MIT) license, "pubrunner" is free and open source software

## Issues

If you encounter any problems, please [file an issue](https://github.com/jakelever/pubrunner/issues) along with a detailed description.

