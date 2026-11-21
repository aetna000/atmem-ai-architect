# Engineering-model depth

Use this reference when producing or refining an implementation handoff. The owner's target is the detail of a professional modeling environment, including class and database designs. Existing prose sections and linear Mermaid sequences are partial projections; populated sections do not establish this level of design.

## Model once, show through connected views

Give model elements stable IDs. Keep their semantic ownership, attributes, operations, constraints and relationships separate from diagram placements, routing and display preferences. A class shown on two diagrams remains one class. A requirement, operation, schema field or test referenced from another view must resolve to its actual model element. Preserve provenance and proposed/accepted status. Keep existing source requirements and decisions intact.

Start with the question a view answers and its audience. Select the appropriate family from diagram-catalog.json. Its registrations are researched capabilities and implementation targets, not proof that AtMem supports each grammar. Frameworks, notation variants, diagrams, matrices and property editors are different kinds of artifact. Use the catalog's sources for the actual notation. Expand incomplete specialized profiles before presenting them as complete support.

## Logical engineering detail

| Concern | Detail the model must carry |
|---|---|
| Classes and interfaces | Responsibility, stereotype, attributes, logical types, visibility, multiplicity, operations, typed parameters and results, preconditions, postconditions, invariants, failure behavior, interfaces implemented, associations and ownership. |
| Relationships | Relationship kind and direction, endpoint roles and multiplicities, navigation, composition/aggregation meaning and constraints. A dependency arrow must not silently stand for containment, data movement and deployment. |
| Conceptual and logical data | Entities, attributes, logical types and units, identifiers, optionality, cardinality, ownership, consistency boundaries, lifecycle, retention and business invariants. |
| Physical storage | Explicit technology mapping, tables/collections, columns, physical types, nullability, ordered composite keys, foreign-key column mappings, referential actions, uniqueness, checks, indexes with query purpose, partitioning where justified, migrations and rollback. Keep unsupported choices proposed. |
| APIs and messages | Named operations/channels, producer and consumer, typed schemas, required/optional fields, units, identity, versions, success and error contracts, correlation, ordering scope, deduplication and recovery. Link operations to the actual interface and schema IDs. |
| Interaction behavior | Lifelines typed by their classifiers, messages linked to operations, parameters/results, synchronous versus asynchronous semantics where known, activations, alternatives with guards, optional paths, loops with bounds, concurrent regions and interaction references. |
| Process behavior | Actor ownership, partitions or pools/lanes, control versus object/message flows, decisions, merges, forks/joins, exception and cancellation paths, compensations and subprocess drill-down. |
| State behavior | Initial/final states, transition triggers, guards, effects, entry/exit behavior, invariants, nested states, concurrent regions and history when the lifecycle needs them. |
| Infrastructure | Artifacts allocated to runtime nodes, site/cloud zones, networks, protocols, identities, storage, brokers, caches, failure domains, operational responsibility, observability, restore and deployment alternatives. |
| Traceability | Source requirement to responsibility, operation, data constraint, behavioral path and acceptance oracle. Keep functional and nonfunctional acceptance distinct and observable. |

Do not invent a language binding to express these concepts. Use logical types and domain vocabulary first. Map to a programming language and physical technologies in explicit separate decisions. React and Angular are UI choices; Kafka, Redis, PostgreSQL and vector databases must be representable in stack and deployment models. Do not insert every technology into every client system. Record the requirement and responsibility that justify a choice, its alternatives and its operational consequences. A vector index used by AtMem memory does not automatically belong in a warehouse control path.

## Views engineers can read and navigate

Show the view name, scope, notation, revision and a useful legend. Use notation-specific symbols: class compartments, visible table keys and types, interface/port symbols, typed arrowheads, multiplicity and guarded transitions. Let shape, labels and line conventions carry meaning independently of color.

Route relationships through deliberate connection points. Keep labels attached to their connector or endpoint. Show actual external participants at a boundary; collapsing all external systems into an anonymous parent loses interface ownership. Use subsystem frames and drill-down to manage density. Hide detail as a view preference while preserving it in the model. Offer a full-detail inspector for attributes, operation signatures, constraints and trace links. Diagrams and their specification tables must describe the same elements.

Provide connected class, logical-data, physical-data, interface, behavior and deployment views where relevant to the component. A context actor may need only an owned integration contract; a persistence module needs the underlying data design. Choose applicable views with a reason rather than generating a fixed set of empty diagrams for every block.

## Handoff and progressive engine support

Carry the detailed engineering model and its diagrams in the module handoff, together with the Spec Kit, plan, dependency-ordered tasks, infrastructure/DevOps specification and acceptance oracles. Link each task to exact model elements and expected deliverables. Preserve original engineering documents and unresolved choices.

When the current canvas projection cannot represent a feature, retain the complete language-neutral design as authored model artifacts with stable IDs and an index. State the missing editor/projection capability explicitly. Do not flatten branching behavior into a linear flow or replace a schema with a paragraph and then call the architecture complete. Split large model artifacts by cohesive module with references rather than truncating detail. The engine still needs shared typed-model storage and full editors/renderers; authored files alone do not deliver those capabilities.

Keep architectural acceptance separate from execution. Showing a diagram, exporting a valid JSON file or passing existing structural checks does not establish the completeness of the design. The next useful review is whether an engineer can implement a real module and its integrations from these models without inventing the missing architecture.
