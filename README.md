# MUD Protocols

MUD protocols implemented in [Python.](https://www.python.org)


## License

MUD Protocols is licensed under the terms of the [Mozilla Public License, version 2.0.](https://nstockton.github.io/mud-protocols/license "License Page")
The code in [mudproto.telnet](https://github.com/nstockton/mud-protocols/blob/master/mudproto/telnet.py)
was originally adapted from the [conch.telnet](https://github.com/twisted/twisted/blob/trunk/src/twisted/conch/telnet.py)
module by Jean-Paul Calderone and others for the [Twisted Project.](https://twistedmatrix.com)
It is licensed under the same [MIT License](https://github.com/twisted/twisted/blob/trunk/LICENSE) as Twisted.


## Credits

This project created and maintained by [Nick Stockton,](https://github.com/nstockton)
with improvements by [Ted Cooke.](https://github.com/BeastlyTheos)

Thanks to [Chris Brannon](https://github.com/cmb) for writing the
[official MPI specification.](https://mume.org/help/mpi) support for MPI in this
project would not exist otherwise.


## Documentation

Please see the [API reference](https://nstockton.github.io/mud-protocols/api "MUD Protocols API Reference") for more information.

## Development

Install the [Python interpreter,](https://python.org "Python Home Page") and make sure it's in your path.

After Python is installed, execute the following commands from the top level directory of this repository to install the module dependencies.
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade --require-hashes --requirement requirements-poetry.txt
poetry install --no-ansi
pre-commit install -t pre-commit
pre-commit install -t pre-push
```
