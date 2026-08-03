# Trader

Project workspace for Anthropic's `financial-services` agent toolkit (https://github.com/anthropics/financial-services).

Installed at user scope, available in this project:

## Named agents (invoke via Agent tool / subagent delegation)
pitch-agent, market-researcher, meeting-prep-agent, earnings-reviewer, model-builder,
valuation-reviewer, gl-reconciler, month-end-closer, statement-auditor, kyc-screener

## Vertical plugins (invoke via slash commands)
financial-analysis, investment-banking, equity-research, private-equity, wealth-management,
fund-admin, operations

## Partner data connectors
lseg, sp-global — require API credentials before use.

All agents draft analyst work product for human review only. None execute trades, bind risk,
approve onboarding, or give investment advice.
