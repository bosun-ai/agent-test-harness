mv tmp/results/results.json tmp/results/results_previous.json
uv run agent_test_harness.py -c example_config.yaml > tmp/results/results.json
killall derrick
killall amsterdam
echo "Killed derrick and amsterdam"
