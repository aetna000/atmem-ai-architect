# Canvas view modes

Owner requested two modes with Components as the default. The single switch now
contains Components and Overview; duplicate tree view actions were removed. Explicit
view choices and overview arrangement persist per project in browser preferences.

Auto-arrange operates on the selected mode. Overview layout changes its projection
without changing component positions, graph membership, connections or design revision.
Component auto-arrange retains its existing component layout behavior.

235 JavaScript tests, build and fixture-session browser checks passed. Browser checks
cover both auto-arrange modes, refresh, per-project preferences, projection isolation
and the existing block/question/requirement editing flow. No model or cloud calls.
