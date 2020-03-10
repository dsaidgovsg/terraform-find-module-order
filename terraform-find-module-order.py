#!/usr/bin/env python3
import argparse
import collections as c
import os
import re
from typing import List, OrderedDict, Set

TF_REMOTE_STATE_DATA_REGEX_STR = r'data "terraform_remote_state" "(\w+)"'
TF_REMOTE_STATE_DATA_RE = re.compile(TF_REMOTE_STATE_DATA_REGEX_STR)

MODULE_EXTRACT_REGEX_STR = r".+/(\w+)"
MODULE_EXTRACT_RE = re.compile(MODULE_EXTRACT_REGEX_STR)


def find_tf_files(start_path: str):
    for root, dirs, files in os.walk(start_path, topdown=True):
        # Filter the list of allowed dirs in-place
        # See: https://stackoverflow.com/a/19859907
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for file in files:
            if file.endswith(".tf"):
                yield (root, os.path.join(root, file))


def extract_remote_state_keys_from_file(path: str) -> List[str]:
    with open(path, "r") as file:
        content = file.read()
        matches = set(TF_REMOTE_STATE_DATA_RE.findall(content))
        return matches


def form_chain_string(chain: List[str]) -> str:
    # Shows apply ordering from base to most derived
    return " > ".join(chain)


def form_dep_string(chain: List[str]) -> str:
    # Showing in reverse order (dep ordering) is clearer for dep tracing
    return " < ".join(chain)


def find_order(mods_x_states: OrderedDict[str, Set[str]]) -> List[str]:
    def impl(mod: str, local_chain: List[str], global_chain: List[str]) -> List[str]:
        # Cyclic dep found as module was found again in local chain
        if mod in local_chain:
            cyclic_dep_str = form_dep_string([mod] + local_chain)
            raise RuntimeError(f"Found cyclic dependencies: {cyclic_dep_str}")

        # Module already done before as part of another chain
        if mod in global_chain:
            return []

        # Some of the modules are from another repo
        # These modules are considered terminal
        states = mods_x_states.get(mod)
        if not states:
            return []

        # Normal chain implementation
        impl_chain = []

        for state in states:
            impl_chain += impl(state, [mod] + local_chain, global_chain)

        return impl_chain + [mod]

    # Start with no elements in global chain
    global_chain = []

    for mod in mods_x_states.keys():
        global_chain += impl(mod, [], global_chain)

    return global_chain


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="terraform-find-cyclic-remote-state")
    parser.add_argument(
        "-e", "--exclude", help="Exclude directories, delimitered by comma"
    )
    parser.add_argument(
        "start_path",
        nargs="?",  # Trick to have an optional positional arg
        help="Start dir path to recursively search for all .tf files. Defaults to ./",
        default="./",
    )

    args = parser.parse_args()

    excluded_dirs = args.exclude.split(",") if args.exclude else []
    start_path = args.start_path

    mods_x_states = c.OrderedDict()

    for module_dir, tf_file in find_tf_files(start_path):
        module_find = MODULE_EXTRACT_RE.findall(module_dir)

        if not module_find:
            raise RuntimeError(
                f"Unable to extract module name from directory {module_dir}"
            )

        # `module_find` has length of at length 1
        module_name = module_find[0]

        if module_name not in mods_x_states:
            mods_x_states[module_name] = set()

        mods_x_states[module_name].update(extract_remote_state_keys_from_file(tf_file))

    ordered_chain = find_order(mods_x_states)
    print(form_chain_string(ordered_chain))
