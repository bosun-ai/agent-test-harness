import logging
import traceback

from pycobertura import Cobertura, CoberturaDiff

def generate_coverage_report(repository_result):
    try:
        coverage_before = Cobertura(repository_result["initial_coverage_tool_output"])
    except Exception as e:
        logging.error(f"Error generating coverage report before: {e}\n{traceback.format_exc()}")
        coverage_before = None

    try:
        coverage_after = Cobertura(repository_result["final_coverage_tool_output"])
    except Exception as e:
        coverage_after = None

    if coverage_before and coverage_after:
        coverage_diff = CoberturaDiff(coverage_before, coverage_after)
    else:
        coverage_diff = None

    return {
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
        "coverage_diff": coverage_diff
    }

def report_results(results):
    agents_stats = []
    for run in results:
        agent_name = run["agent_name"]
        repository_stats = []
        logging.info(f"Organizing results for agent run {run['run']}")
        benchmark_result = run["result"]
        repository_url = run["repository_url"]
        llm_metrics = benchmark_result["llm_metrics"]
        run_id = run["run"]
        models = list(set([llm_metric["model_name"] for llm_metric in llm_metrics]))

        coverage_report = generate_coverage_report(benchmark_result)
        coverage_after = coverage_report["coverage_after"]
        coverage_before = coverage_report["coverage_before"]
        coverage_diff = coverage_report["coverage_diff"]

        repository_stats.append({
            "repository_url": repository_url,
            "run_id": run_id,
            "successful": coverage_after is not None,
            "coverage_before": {
                "line_rate": coverage_before.line_rate(),
                "branch_rate": coverage_before.branch_rate(),
                "total_statements": coverage_before.total_statements(),
                "total_misses": coverage_before.total_misses(),
            } if coverage_before else None,
            "coverage_after": {
                "line_rate": coverage_after.line_rate(),
                "branch_rate": coverage_after.branch_rate(),
                "total_statements": coverage_after.total_statements(),
                "total_misses": coverage_after.total_misses(),
            } if coverage_after else None,
            "coverage_diff": {
                "line_rate": coverage_diff.diff_line_rate(),
                "total_statements": coverage_diff.diff_total_statements(),
                "total_misses": coverage_diff.diff_total_misses(),
            } if coverage_diff else None,
            "agent_execution_time": benchmark_result["agent_execution_time"],
            "total_completion_tokens": sum([llm_metric["completion_token_count"] for llm_metric in llm_metrics]),
            "completions_count": len(llm_metrics),
            "total_prompt_tokens": sum([llm_metric["prompt_token_count"] for llm_metric in llm_metrics]),
            "total_token_count": sum([llm_metric["total_token_count"] for llm_metric in llm_metrics]),
            "models": [
                {
                    "name": model,
                    "completions_count": len([llm_metric for llm_metric in llm_metrics if llm_metric["model_name"] == model]),
                    "total_completion_tokens": sum([llm_metric["completion_token_count"] for llm_metric in llm_metrics if llm_metric["model_name"] == model]),
                    "total_prompt_tokens": sum([llm_metric["prompt_token_count"] for llm_metric in llm_metrics if llm_metric["model_name"] == model]),
                    "total_token_count": sum([llm_metric["total_token_count"] for llm_metric in llm_metrics if llm_metric["model_name"] == model]),
                } for model in models
            ]
        })

        successful_repositories = [repository_stat for repository_stat in repository_stats if repository_stat["successful"]]

        def get_model_stats(model):
            stats = []
            for repo in repository_stats:
                for model in repo["models"]:
                    if model["name"] == model:
                        stats.append(model)
            return stats

        agent_stats = {
            "name": agent_name,
            "runs": repository_stats,
            "total_completion_tokens": sum([repo["total_completion_tokens"] for repo in repository_stats]),
            "total_prompt_tokens": sum([repo["total_prompt_tokens"] for repo in repository_stats]),
            "total_token_count": sum([repo["total_token_count"] for repo in repository_stats]),
            "runs_count": len(repository_stats),
            "successful_runs_count": len(successful_repositories),
            "average_coverage_diff": sum([repo["coverage_diff"]["line_rate"] for repo in successful_repositories]) / len(successful_repositories) if successful_repositories else None,
            "average_agent_execution_time": sum([repo["agent_execution_time"] for repo in repository_stats]) / len(repository_stats) if repository_stats else None,
            "average_coverage_before": sum([repo["coverage_before"]["line_rate"] for repo in successful_repositories]) / len(successful_repositories) if successful_repositories else None,
            "average_coverage_after": sum([repo["coverage_after"]["line_rate"] for repo in successful_repositories]) / len(successful_repositories) if successful_repositories else None,
            "models": [
                {
                    "name": model,
                    "total_completion_tokens": sum([model_stat["total_completion_tokens"] for model_stat in get_model_stats(model)]),
                    "total_prompt_tokens":     sum([model_stat["total_prompt_tokens"] for model_stat in get_model_stats(model)]),
                    "total_token_count":       sum([model_stat["total_token_count"] for model_stat in get_model_stats(model)]),
                } for model in models
            ]
        }
        agents_stats.append(agent_stats)
    return agents_stats