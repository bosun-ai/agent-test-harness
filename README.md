# Code Writing Agent Benchmark Harness

Initially we want to support these types of benchmark:

### 1. A test running benchmark:
The goal of this benchmark is to generate the scripts/environment to be able to run the tests.

### 2. A test writing benchmark

The goal of this benchmark is to generate additional tests that increase the test coverage of the test suite of a project.

## Test running benchmark details

The qualities that are measured in this benchmark:
  - Is (the lack of) existing test tooling accurately determined, and in how many tokens?
  - Is a successful setup script and test invocation determined, and how many lines are reported to be covered, and in how many tokens?(note, this step might be gamed, so it should be manually policed)

## Test Writing Harness details

The qualities that are measured in this benchmark:
  1. Wether the agent successfully adds tests
  2. How much test coverage it adds
  3. How many modifications it does to achieve that test coverage
  4. How many tokens it spends to do so.

To get `1` and `2`, we need to run the coverage command ourselves. So we need the workspace and the command.
To get `3` we can just count changes of a `git diff` inside the workspace.
To get `4` we can consult the LLM proxy.

## Establishing the agent

An agent needs an environment to write code and run tools in, we use a workspace provider to establish a clean environment
for the agent to do its work in. The agent will also need an LLM for creative output, we will use an LLM proxy to provide
access to an LLM.

### Steps

1. Provide the LLM proxy
2. Provision the git repository
3. Provision a workspace with a copy of the git repository
5. Run the coverage tool inside the workspace to establish a baseline
4. Run the agent inside the workspace
5. Run the coverage tool again to determine improvements
6. Run a git diff between the original git repo and the version in the workspace to measure impact