# Use Metapyle as the sole data-access API

Kairopsis accesses market data through Metapyle. Keeping provider integrations
behind that boundary lets the dashboard focus on investigation and retained
evidence rather than provider-specific connection logic.

An installation may select a compatible Metapyle distribution through its
approved package route. Provider configuration, authentication and private
implementation changes remain outside the public Kairopsis package. Adapter
capabilities and observation semantics must be verified in the target environment.
