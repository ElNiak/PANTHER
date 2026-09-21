"""campaign init exactly as the CLI builds it, with toolchain verification skipped.

The CLI refused: "toolchain verify failed: the example did not build offline".
Everything else (argv parsing and defaults, the plugin dir, the renderer) is the
snapshot's own code path.
"""

import argparse
import sys
from pathlib import Path

from ai_rfc.experiment import cli as experiment_cli
from ai_rfc.experiment.config import CampaignConfig, init_campaign

argv = sys.argv[1:]
parser = argparse.ArgumentParser(prog="ai-rfc experiment")
experiment_cli.configure(parser)
args = parser.parse_args(argv)
assert args.command == "campaign" and args.verb == "init", args

root = args.root.resolve()
campaign = init_campaign(
    CampaignConfig(
        root=root,
        campaign_id=args.id,
        pristine_dir=Path(args.baseline),
        arms=args.arms,
        repeats=args.repeats,
        seed=args.seed,
        model=args.model,
        effort=args.effort,
        budget_usd=args.budget,
        timeout_s=args.timeout,
        plugin_root=experiment_cli._default_plugin_dir().resolve(),
        python=args.python,
        claude_bin=args.claude,
        parity=None,
        session_mode=args.session_mode,
        toolchain=args.toolchain.resolve(),
        verify_toolchain=False,
        consolidate_every=experiment_cli._consolidation_interval(
            args.consolidate_every, args.config
        ),
    )
)
print("campaign:", campaign.dir)
print("plugin_root:", campaign.plugin_root)
print("run order:", " ".join(campaign.run_order))
