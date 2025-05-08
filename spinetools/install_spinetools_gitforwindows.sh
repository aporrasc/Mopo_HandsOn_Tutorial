#!/Scripts/bash
#chmod +x ~/spinetools/install_spinetools.sh
# check whether python, git and julia are installed; python may be needed to changed to python depending on your system
python --version
git --version
julia --version

# user settings: install directory, environment names
path_spinetools=$(dirname $0)
path_envs=environments
env_python=penv
# the julia settings need to be adjusted directly in the code (see further below)

# download files from git
cd $path_spinetools
git clone https://github.com/spine-tools/Spine-Toolbox.git
git clone https://github.com/spine-tools/SpineInterface.jl.git
git clone https://github.com/spine-tools/SpineOpt.jl.git

# branch
cd SpineInterface.jl
git fetch --tags
git checkout v0.15.2
cd ..

cd SpineOpt.jl
git fetch --tags
git checkout v0.10.2
cd ..

cd Spine-Toolbox
git fetch --tags
git checkout v0.9.6
cd ..

# create python environment (for spine toolbox)
mkdir $path_envs
cd $path_envs
python -m venv $env_python
source $env_python/Scripts/activate
cd ..

# alternatively use a conda environment
#path_conda=~/miniconda3/etc/profile.d/conda.sh
#env_conda=cenv_dev
#source $path_conda
#conda create --name $env_conda python=3.9 -y
#conda activate $env_conda

#python -m pip install --upgrade pip

# Configure PyCall
julia -e '
env_julia = joinpath(@__DIR__,"environments","jenv")
path_python = Sys.which("python")
import Pkg
Pkg.activate(env_julia)
ENV["PYTHON"] = path_python
Pkg.add("PyCall")
import PyCall
println(PyCall.pyprogramname)
'

# install python requirements
#python -m pip install -r dev-requirements.txt
cd Spine-Toolbox
python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt 
cd ..

# install SpineInterface
cd SpineInterface.jl
julia -e '
env_julia = joinpath(dirname(@__DIR__),"environments","jenv")
path_spineinterface = joinpath(@__DIR__)
import Pkg
Pkg.activate(env_julia)
Pkg.develop(path=path_spineinterface)
Pkg.instantiate()
'
cd ..

# install SpineOpt
cd SpineOpt.jl
julia -e '
env_julia = joinpath(dirname(@__DIR__),"environments","jenv")
path_spineopt = joinpath(@__DIR__)
import Pkg
Pkg.activate(env_julia)
Pkg.develop(path=path_spineopt)
Pkg.instantiate()
'
cd ..

# manually add julia environment to settings in spine toolbox
spinetoolbox

# install spineopt plugins as well

# alternatively keep shell open for debugging
$SHELL