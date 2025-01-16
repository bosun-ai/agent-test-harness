# Extracted repos from SWE-Bench

Our reference is at commit [5f5a7d](https://github.com/swe-bench/SWE-bench/tree/5f5a7df799663adba4b191eca3d675faf3621fe2/swebench/harness) because later commits restructure the repo.

In the file `swebench/harness/constants.py` there are custom environment instructions for setting up each repo. In the
`SWE-Bench` dataset each entry maps to a repo and a version of that repo. Each version of the repo has a different
environment setup.

Our goal is to generate a template for each repo + version combination. In `docker_build.py` there's a function 
`build_base_images` that builds the base images, it does so based on `get_test_specs_from_dataset` values.

