f=${BASH_ARGV[0]:-$0}
export PYTHONPATH=$PYTHONPATH${PYTHONPATH:+:}$(dirname $(readlink -f "$f"))
export PYTHONPATH=$PYTHONPATH${PYTHONPATH:+:}$(dirname $(dirname $(readlink -f "$f")))
. ./venv/bin/activate
