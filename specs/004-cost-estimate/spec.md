# Feature Specification: Cost estimate

**Feature Branch**: `004-cost-estimate`

**Created**: 2026-11-05

**Status**: Release-1 slice built — see tasks.md

**Input**: Journey step 4 — "Show estimated cloud costs, usage assumptions and the main cost drivers. Estimates are not bills or guarantees." Action 6 — "a cost model with explicit inputs and assumptions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A monthly estimate with visible inputs (Priority: P1)

The user opens Estimate and sees a monthly range (low / expected / high) for the design, broken down by component and by cost driver (model tokens, endpoint hours, storage, data transfer, requests). Every number traces to a usage input and a unit price, each with a source and date.

**Independent Test**: Load a template, enter usage (requests/month, tokens/request) and unit prices; the total equals the sum of driver lines; changing one input updates only the dependent lines.

**Acceptance Scenarios**:

1. **Given** usage inputs and unit prices, **Then** each line shows quantity × unit price = cost, with units.
2. **Given** a missing unit price, **Then** the line shows "price needed", is excluded from the total, and an open question is created; the total is labelled incomplete.
3. **Given** any estimate, **Then** it is labelled "Estimate — not a bill or guarantee" with the price-book date.

---

### User Story 2 — See what drives cost and what changes it (Priority: P1)

The estimate highlights the top three drivers and lets the user vary a usage input (e.g. ×2 requests) to see the effect. Saved scenarios are kept in the project.

---

### User Story 3 — Prices from a source, not invented (Priority: P2)

Unit prices come from a price book: entered by the user, imported from a file, or (when connected) retrieved from the provider's published pricing with URL and retrieval date. AtMem AI Architect never fills a price without a source.

**Acceptance Scenarios**:

1. **Given** a price retrieved from a provider page, **Then** it shows URL, region, currency and retrieval date.
2. **Given** a price older than 90 days, **Then** it is flagged for review (review date, not deletion).

### Edge Cases

- Mixed currencies: refused unless the user provides an exchange rate with date.
- Free tiers and commitments (reservations, savings plans): modelled as explicit adjustments with their own assumptions.
- Agent-run costs (Adflow traces) are never mixed into the architecture estimate.

## Requirements *(mandatory)*

- **FR-001**: The estimate MUST be computed only from usage inputs and unit prices stored in the project.
- **FR-002**: Each component kind MUST map to one or more cost drivers with a formula and units.
- **FR-003**: Each unit price MUST record provider, service, SKU or description, region, currency, unit, price, source (user, file, provider page), URL, and date.
- **FR-004**: The system MUST show low / expected / high using explicit multipliers or input ranges, not hidden factors.
- **FR-005**: Missing inputs MUST produce open questions (002) and mark the estimate incomplete.
- **FR-006**: The estimate MUST be included in the deployment document (005) with all inputs and assumptions.
- **FR-007**: A default price book for the first validated provider MAY ship only with sources and dates [NEEDS CLARIFICATION: first provider — OD-1].

### Key Entities

- **Usage input** (name, value, unit, period, source, date), **Unit price**, **Cost driver**, **Estimate line**, **Scenario**.

## Success Criteria *(mandatory)*

- **SC-001**: For three priced reference designs, expected estimate within ±25% of a hand-priced calculation using the same price book.
- **SC-002**: 100% of estimate lines trace to an input and a priced source, or are shown as incomplete.

## Assumptions

- Release 1 estimates monthly run cost; build and migration cost are out of scope.
