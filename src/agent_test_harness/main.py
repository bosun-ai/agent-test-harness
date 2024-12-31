"""Main entry point for the agent test harness CLI"""
from .cli import Cli

def main() -> None:
    cli = Cli()
    cli.parse_args()
    cli.initialize()
    cli.execute()

if __name__ == "__main__":
    main()
