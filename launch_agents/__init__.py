"""launch_agents: the backend package of the product (ADR-0024).

Layering (checked by reviewers):

    domain  <-  config, reliability  <-  llm, ports  <-  rules, signoff, persistence, accounts,
                team, access, email, billing, jobs, pdf, security, observability, agents/*
            <-  orchestrator, pipelines  <-  workflows, notifications, privacy, admin
            <-  composition  <-  api, demo

The customer-facing brand name lives only in ``domain/constants.py`` (ADR-0039).
"""
