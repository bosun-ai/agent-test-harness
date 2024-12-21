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

### Agent environment

Besides access to the LLM and the workspace, the agent might have external dependencies that need to be running. For this
we can use docker compose to start the dependencies. So an agent might consist of two things:

1. A docker compose file to start the dependencies
2. A configuration for the agent that contains the workspace setup script and the command to run the agent.

We also need a way to pass the LLM proxy address to the agent through the workspace provider.


## Implementation

### Workspace provider

We've implemented a workspace provider in Derrick.

### LLM proxy

We've implemented a LLM proxy in Amsterdam.

## Persisting results

We need to store the results of the benchmark. Right now it just dumps the output to a json file.

Things that we would like to be able to do:

- Contribute individual results

We could:

- Simply load the json file, add the new result, and save it again.
- Connect to a database, and store the results there.

If we do that, it would be nice if we would host it so we could run benchmarks
wherever and submit the results.

Then we need a server that exposes an API to submit results and query them.

We need to host that server somewhere.

# TODOS

- [ ] Pick 3 small projects, 3 medium projects, 2 large projects for the initial benchmark, for each platform (rust, typescript, python)
- [X] Decide how to persist the results of the benchmark
- [X] Timeout in derrick


## Project choices

### Rust

#### Small <10k lines

- tokei https://github.com/XAMPPRocky/tokei

#### Medium <100k lines

- ripgrep https://github.com/BurntSushi/ripgrep


#### Large >100k lines

- [ ] 


### Typescript / Javascript

#### Small <10k lines

- todolist https://github.com/bosun-ai/todolist
- 

#### Medium <100k lines

- rrweb https://github.com/rrweb-io/rrweb
- mermaid https://github.com/mermaid-js/mermaid

#### Large

- [ ]


### Python

#### Small <10k lines

- gpt-migrate https://github.com/joshpxyne/gpt-migrate

#### Medium <100k lines

- llama-stack https://github.com/meta-llama/llama-stack

#### Large >100k lines

- Apache Airflow https://github.com/apache/airflow
