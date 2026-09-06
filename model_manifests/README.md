# Frozen model manifests

Certification model manifests live here. Real weights stay outside source control, but every evaluator used for measured evidence must have a manifest with the exact architecture, weight identifier, SHA-256, framework/runtime version, preprocessing, class mapping, and decision threshold.

Do not commit placeholder manifests and do not issue a certificate when a referenced weight hash cannot be verified.
