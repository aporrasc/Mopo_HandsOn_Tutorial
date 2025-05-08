#!/Scripts/bash
#chmod +x ~/inestools/install_inestools.sh

# This script assumes that the install_spinetools.sh script has run successfully.

# user settings: install directory, environment names
path_inestools=$(dirname $0)
path_envs=environments
env_python=penv
# the julia settings need to be adjusted directly in the code (see further below)

# download files from git
cd $path_inestools
git clone https://github.com/ines-tools/ines-tools.git
git clone https://github.com/ines-tools/ines-spineopt.git
git clone https://github.com/ines-tools/data-pipelines.git
git clone https://github.com/ines-tools/ines-spec.git
#git clone https://github.com/ines-tools/ines-certify.git

# branch
#cd SpineOpt.jl
#git fetch --tags
#git checkout v0.15.2
#cd ..

# open python environment (for spine toolbox)
cd $path_envs
source $env_python/Scripts/activate
cd ..

# install python requirements
python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements_python.txt

# install ines tools
cd ines-tools
pip install .
cd ..

# alternatively keep shell open for debugging
$SHELL