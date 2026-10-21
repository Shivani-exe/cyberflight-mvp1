# Limitations

These are four selected, baseline-clean attack windows, not a prospective production trial. Costs count stored rows, not bytes or money. The static seed 42 result is one computer sample; see the multi-seed distribution and separate row-level sampling result.

The fanout ratio is add-one smoothed: (window + 1) / (baseline + 1). It misses repeated use of an existing edge, including the documented cluster 21 attack. Alert counts include many computers without labeled attack rows. Labels are incomplete ground truth, so these are apparent false alarms.

The fixed policy was selected using these windows. Held-out results select parameters on the other three clusters, then evaluate on the named held-out cluster; this small retrospective split does not establish deployment performance. Clusters may share computers.

The pre-alert buffer assumes a temporary local recorder exists. Resource limits, alert delivery delays, privacy, and recorder loss are not modeled. LLM plans are proposals only; deterministic validation and simulation do not authorize real collection. No evidence of LLM improvement is claimed before a live evaluation.
