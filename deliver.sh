#!/bin/sh -x

# A script to create an Zip or Tar archive of all necessary source
# files which can be delivered to a customer via email or some other
# method other than Git.

die() { echo "${@}" >&2; exit 1; }

require() {
    if ( "${1}" --version >/dev/null 2>&1 ); then
        return 0;
    else
        die "Required command \"${1}\" not available."' (Check PATH environment variable?)';
    fi;
}

require find;
require xargs;
require date;

USAGE="$0  [-z | --zip | -g | --tgz | -l | --list]

Flags:

-z --zip    Creates a .zip archive of all files

-g --tgz    Creates a .tgz (.tar.gz) archive of all files

-l --list   Prints a list of all files that will be included in the archive
"

CMD="${1}";
if [ -n "${CMD}" ]; then shift; fi;

SEARCH_DIRS="${@}";
if [ -z "${SEARCH_DIRS}" ]; then SEARCH_DIRS='.'; fi;

RUN='';
case "${CMD}" in
    ('--zip') RUN=run_zip;;
    ('-z') RUN=run_zip;;
    ('--gzip') RUN=run_gzip;;
    ('-g') RUN=run_gzip;;
    ('--list') RUN=run_list;;
    ('-l') RUN=run_list;;
    (*) die "${USAGE}";;
esac;

OUT_BASENAME="$(date '+data-prep-kit_%Y-%m-%d'; )";

run_find() {
    find "${SEARCH_DIRS}" \
       -type d \
       \( -iname .git \
       -o -iname env \
       -o -iname .mypy_cache \
       -o -iname __pycache__ \
       -o -iname 'example.py' \
       \) -prune -false -o \
       -type f \
       \( -iname '*.py' \
       -o -iname '*.txt' \
       -o -iname '*.md' \
       \) -print0;
}

run_list() {
    run_find | xargs -n 1 -0 printf '%s\n';
}

run_zip() {
    require zip;
    FILENAME="${OUT_BASENAME}.zip";
    run_find | xargs -0 zip -D -9 "${FILENAME}";
}

run_gzip() {
    require tar;
    FILENAME="${OUT_BASENAME}.tar.gz";
    run_find | xargs -0 tar czvf "${FILENAME}";
}

"${RUN}";
