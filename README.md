# `terraform-find-module-order`

Python script to find the order of `terraform apply` / `terragrunt apply` in a
repository with a bunch of related Terraform modules.

It can also be used to find any cyclic dependency amongst the Terraform modules.

Requires Python 3.7 and above.

## Example run

```bash
# Excludes dirs environments and vendor
python3 terraform-find-module-order.py -e environments,vendor path/to/root/module

# Possible outputs

# Invalid cyclic dependencies
# RuntimeError: Found cyclic dependencies: xxx < yyy < xxx

# Valid ordering
# xxx > yyy > zzz > aaa
```

## How does this work

The script greps for all `data "terraform_remote_state" "xxx"` in all `.tf`
files found recursively from the start path (defaults to `./`).

`xxx` refers to the module name. The `xxx` module name is extracted and all the
extracted module names are grouped according to the Terraform module directory
that it falls within, i.e. by per directory, similar to `terraform apply` works.

If there is a cyclic dependency, the script will raise an error and immediately
flag out the found cyclic dependency trace.

Otherwise if there is no cyclic dependency, the script will print the chain of
Terraform modules to apply from left to right.

## Assumptions required to work

This script requires the following assumptions:

1. All the modules are properly `terraform fmt`-ed.
2. Given `data "terraform_remote_state" "xxx"`, `xxx` is assumed to be named the
   same as the Terraform module dir name in the search path. If such a Terraform
   module dir name cannot be found, the remote state is assumed to be referring
   to some external module dir name whose ordering cannot be determined.
3. If a module dir has no remote state, or only remote states with external
   module dirs, this module dir is considered a terminal point of the dependency
   chain.
