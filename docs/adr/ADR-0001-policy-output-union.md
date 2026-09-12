# ADR-0001: Policy output is a discriminated union

Status: accepted

The original nullable-bag representation admitted impossible combinations such as `mode=block` with a live tool call. `PolicyOutput` is therefore a union discriminated by `mode`:

- `execute`, `sandbox`, and `rewrite` require a tool, arguments, and proof;
- `ask` requires a question and missing fields;
- `block` requires a reason code;
- `stop` requires a reason code and safe-stop termination.

This changes the representation, not the research semantics. The canonical logical fields remain mode, termination, tool/args, source bindings, authorization bindings, proof, and scope, but only legal combinations can be instantiated.

