from setuptools import setup
setup(
    name='motif',
    version='0.0.1',
    entry_points={
        'console_scripts': [
            'motif=run:Runner',
            'motif-list=run_list:ListRunner'
        ]
    }
)


#######################################################
# This project can be installed using the following command:
# $ pip install -e /path/to/script/folder --target /path/to/script/folder
# $ pip install -e /path/to/script/folder --user      # install the library into user home directory: $HOME/.local/bin
# The option '-e' stands for editable, meaning you can continue to edit your source code without reinstall the code
# The option '--target' sets the installation directory for this library,
#      but you should add this target path to the env PYTHONPATH (for importing) or PATH (for executing)
# The option '--user' sets the installation directory for this library,
#      but you should add "$HOME/.local/bin" to the env PATH
# Example:   (Execute in each machine)
# $ pip install -e ./ --user
# $ export PATH=$(realpath "./.local/bin"):$PATH
# $ export PYTHONPATH=$(realpath "./.local/bin")
# References:
# https://stackoverflow.com/questions/56986667/how-to-use-static-files-included-with-setuptools
# https://stackoverflow.com/questions/27494758/how-do-i-make-a-python-script-executable
# https://stackoverflow.com/questions/2915471/install-a-python-package-into-a-different-directory-using-pip
#######################################################
