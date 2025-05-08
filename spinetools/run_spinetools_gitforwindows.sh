#!/bin/bash
#chmod +x ~/spinetools/run_spinetools.sh

#user settings: environment directory, environment names
path_spinetools=$(dirname $0)
env_python=environments/penv
#julia settings in julia code below

# open spine toolbox
cd $path_spinetools
source $env_python/Scripts/activate
spinetoolbox

#keep shell open for debugging
#$SHELL