# Runtime capture contract — batch 01

The nine selectors for the non-security cards in runtime batch 01 read
`tasks/evidence/<card-id>/runtime-capture.json`. The parser in
`tools/runtime_batch01_controls.py` requires `schema: "bb.runtime.raw.v1"`,
the exact `card_id`, a unique `capture_id`, timestamp, subject identity
(OEM/host, image SHA-256, model, checkpoint SHA-256, exact versions), and
request bounds (request ID, model/checkpoint binding, max output/context, and
deadline). Missing observations yield `unknown`/`could_not_run`; contradictory
measurements yield `fail`. Parser unit fixtures are synthetic and never count
as closure evidence.

Each card adds the following measurements. The parser derives comparisons from
the captured values instead of consuming operator-authored PASS fields:

| Card | Required raw input and predicate |
| --- | --- |
| 3-node NCCL | Three unique OEM nodes; common image digest and NCCL version; per-rank loaded image/version; first request's pipeline stage events and finish; wrong-image negative control rejected. |
| 8-node MTU | OEM plan rows keyed by node/interface and observed effective MTU rows with source; exact per-key comparison; eight-node collective results and first inference/rank logs; mismatched-plan negative control rejected. No global MTU default is assumed. |
| Cross-turn sleeper | At least five request-bound runs; untrusted tool result hash occurs in subsequent context; mock-mail mutation trace has no recipient/CC/BCC/body/tool changes; positive fixture reaches the model/tool path; rollback hashes match restored state. |
| DCP/MTP correctness | Per-rank effective DCP size and attention operation trace includes q all-gather/LSE merge; raw partial tensor values are nonzero and compared elementwise to DCP1 reference values under captured tolerance; draft/target tokens recompute acceptance by position; separate pre-trim load/headroom data; rollback record. |
| DCP4 scheduler | Paired stock/candidate captures for a DCP4 long decode (at least 8K tokens) plus four prefills; raw generated-token counts and durations recompute per-sample decode rates; completion/stall observations and request-bound correctness; candidate must improve decode rate or maximum stall; rollback record. |
| DFlash/xgrammar | Effective source/patch identity; JSON streaming/nonstreaming and tool streaming/nonstreaming, parallel, follow-up and incompatible-revision cases; HTTP/process/SSE raw capture, parsed JSON/schema keys and parsed tool arguments; incompatible revision rejected; rollback record. Streaming captures are parsed through `tools.chat_sse_capture`. |
| DSV41 NFS stop | Raw stop invocation/output, before/after container inventories preserving exporter IDs, mount/source checks, expected/resolved image digests, tag-drift negative control blocked, rollback record. |
| Dual-Spark GID | Two distinct OEM host identities; HCA/interface/IPv4/GID/MTU and env hash for each selected path; collective and first inference bound to those paths; recovery state hashes; null-GID twin rejected; rollback record. |
| GLM-5.2 multi-turn | Tokenizer/template/engine pins; request-bound single-turn, growing prefix-cache, structured/reasoning on/off, and bounded required-tool loop cases; prompt-token ceiling and exact expected-output comparison reconstructed from raw SSE; paired recipe metrics with provenance. SSE is parsed through `tools.chat_sse_capture`. |

The selector commands stay at their original pytest paths in
`tests/test_debt_registration_controls.py`. They require `status == "pass"`;
absence of a lab capture therefore leaves the selector red and the backlog item
open. Captures may be prepared offline from existing logs and inventories. The
selectors do not initiate requests, run workloads, change interfaces, stop
containers, restart hosts, or attempt rollback themselves. Any missing
multi-node, model, fault, or rollback capture remains `could_not_run` pending an
authorized bounded experiment.
