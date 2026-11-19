# Enterprise modeling research and implementation basis

Research in progress, 19 November 2026. The owner rejected the existing diagrams and handoff depth. Previous export, rendering and reference-check results remain evidence of their narrow checks; they do not meet the requested architectural standard. Work has shifted from validating that output to researching and implementing professional modeling depth.

The product target is a generic architecture engine. LSKD/TAL/Libiao WCS is the working example. The owner wants the usable depth of Enterprise Architect and StarUML, including class and database models, without choosing a programming language at this stage. Modern technology choices must be representable separately: React/Angular, Kafka, Redis, PostgreSQL and vector databases. Existing business requirements, ownership and accepted decisions remain authoritative.

## What the research establishes

Enterprise Architect organizes a repository of model elements and relationships into different views. A diagram is a presentation of selected elements; the same element can appear in several diagrams. Its UML catalogue distinguishes seven structural and seven behavioral diagram types. Domain profiles and extended diagrams add other grammars. A finite list of standard types does not enumerate every custom MDG technology a user can install. Sources: [UML families](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_languages/umldiagrams.html), [model elements](https://sparxsystems.org/enterprise_architect_user_guide/17.2/modeling_fundamentals/workingwithumlelements.html), [perspectives](https://sparxsystems.org/enterprise_architect_user_guide/17.2/modeling_fundamentals/perspectives.html).

The first machine-readable catalogue is [diagram-catalog.json](../../../agent-skills/specialists/enterprise-architecture/references/diagram-catalog.json). It records diagram families, elements, relationships, property groups, questions answered, sources and current authoring limits. Entries distinguish diagrams, notation variants, profile families, viewpoints, tables and other editors. Registering a name does not implement its semantics or renderer.

| Inventory | Current research coverage |
|---|---|
| UML | All 14 standard diagram types; information flow recorded separately as an additional supported modeling view. |
| SysML | Nine diagram families, including requirements, blocks, internal connections, parametrics and behavior. Version-specific semantics remain to be expanded. |
| BPMN | Process, collaboration, choreography and conversation; participant, event, activity, gateway and flow palettes identified. |
| ArchiMate | The 25 viewpoints listed by EA's four current viewpoint groups; elements span enterprise intent through technology. |
| Data | Conceptual, logical and physical models; ERD; UML, Information Engineering and IDEF1X connector notations. |
| Decisions | DMN decision requirements, decision tables and expressions, with diagram/table/editor distinctions. |
| Other domains | EA analysis, requirements, maintenance, strategy, user interaction, information flow, service, cloud and specialized profile families registered. Detailed specialized grammars and framework subview grids remain incomplete. |

Sources: [SysML toolboxes](https://www.sparxsystems.org/enterprise_architect_user_guide/17.2/modeling_languages/systoolb.html), [BPMN diagram types](https://www.sparxsystems.org/enterprise_architect_user_guide/17.2/modeling_languages/bpmn_2_0_toolbox_pages.html), [ArchiMate viewpoints](https://www.sparxsystems.org/enterprise_architect_user_guide/17.2/modeling_languages/archimate-viewpoints.html), [data notations](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_domains/data_modeling_notations.html), [DMN](https://www.sparxsystems.org/enterprise_architect_user_guide/17.2/modeling_languages/dmn_modeling_and_simulation.html).

## Four capabilities that must stay distinct

1. Diagram grammar: the types of elements and legal relationships in a notation.
2. Semantic properties: the actual attributes, operations, keys, constraints, guards, messages and allocations represented by those elements.
3. Visual presentation: symbols, compartments, arrowheads, endpoint labels, frames, routing, layering and display preferences.
4. Modeling interaction: reuse, drill-down, property editing, undo/redo, cross-view navigation, source traceability and change impact.

A palette and attractive boxes cover only a fraction of this. A detailed model must connect class operations to messages and interfaces, entities to storage constraints, state changes to behavior, and all of these to requirements and acceptance oracles. The target design is described in [modeling-depth.md](../../../agent-skills/specialists/enterprise-architecture/references/modeling-depth.md). This is an implementation basis, not a statement that those editors already exist.

## Visual and semantic findings

Class views need compartments for names, attributes, operation signatures and constraints, along with relationship roles and multiplicities. Component views need provided/required interfaces and ports. Composite views describe parts and their interactions, not simply another level of boxes. Database diagrams need visible columns and keys plus an inspector for composite keys, foreign-key mappings, uniqueness, checks and indexes. Sequence diagrams need typed lifelines and combined fragments for alternatives, repetition and concurrency. State and activity diagrams need their actual guards, effects and control/object-flow distinctions. Sources: [class notation](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_languages/classdiagram.html), [component notation](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_languages/componentdiagram.html), [composite structure](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_languages/compositestructurediagram.html), [database constraints](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_domains/edit_constraints.html), [interaction operators](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_languages/interactionoperators.html).

EA also distinguishes formal notation from presentation styles. Orthogonal, direct, routed, tree and custom connectors are layout choices. Custom/simple, rectangular, whiteboard and hand-drawn styles change presentation; they do not replace the model's type or meaning. Swimlanes, matrices, legends, filters and compartments provide controlled views of detail. AtMem should retain complete element data while allowing focused views. Sources: [connector styles](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_fundamentals/stylemenusection.html), [custom styles](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_fundamentals/diagram_customstyle.html), [rectangle notation](https://www.sparxsystems.org/enterprise_architect_user_guide/17.2/modeling_fundamentals/usingrectanglenotation.html), [swimlanes](https://sparxsystems.org/enterprise_architect_user_guide/17.2/modeling_fundamentals/swimlanes.html).

The current AtMem buildSpec supports eight prose sections and ordered scenario steps. Its sequence/function/event diagrams project those steps, and its nested canvas collapses external participants onto a scope node. These structures cannot express the requested class and database detail or preserve all boundary identities. The engine needs a shared typed engineering model and notation-specific views. Adding Mermaid files or more prose alone does not resolve this limitation.

## StarUML 8.1.0 local study

The supplied machine contains StarUML-8.1.0-arm64.dmg in Downloads. It was mounted read-only, and StarUML was opened from it. Existing client models and application settings were not edited. macOS denied Accessibility automation and display capture, so no interactive GUI editing or application screenshot inspection is claimed.

The documented native CLI works. A separate, original language-neutral learning model was authored in private scratch space and exported by StarUML to SVG and PNG. It contains a class view showing visibility, logical attribute types and operation return types, and a logical data view showing columns and PK/FK flags. Both native PNGs were visually inspected. The exports display UNREGISTERED watermarks; those remain intact. This does not establish that every installed profile is licensed or operational.

A read-only inventory of shipped metamodel names identifies UML, SysML, BPMN, ERD, DFD, flowchart, mind map, C4, wireframe and AWS/Azure/GCP families. Raw application metamodel definitions and proprietary images are not copied into AtMem. The implementation will use original rendering of standard notation. This inventory, the sandbox model and native exports remain under .local/enterprise-modeling-research. Sources: [current capabilities](https://docs.staruml.io/), [CLI](https://docs.staruml.io/user-guide/cli-command-line-interface/), [model/view API](https://docs.staruml.io/developing-extensions/scripting-api/), [undo-aware editing](https://docs.staruml.io/developing-extensions/creating-deleting-and-modifying-elements/).

## Next work in the owner's order

Complete the catalogue research before claiming full notation coverage: expand the remaining framework subviews, individual element/relationship/property constraints and style controls, and distinguish edition/profile/version boundaries. Keep normative references separate from product implementation behavior. No installed-product or standards conformance claim follows from this inventory.

Bring that catalogue into engine-owned skills and tools, then implement shared model identity and language-neutral class/schema detail. Follow with first-class interfaces, behavioral fragments, process/state models, deployment mapping and connected inspectors. Use the generic engine to produce the detailed LSKD architecture from its original sources; do not handcraft a separate LSKD-only generator or retrofit unsupported fields into an immutable prior proposal. Preserve the existing output as the insufficient baseline.

Architectural completion requires concrete module designs and integrated views that an implementation team can use without inventing the missing architecture. Existing vendor/source disagreements must remain explicit. External agent execution, enterprise maintenance, orchestration, scale and deployed-system qualification remain separate unfinished work. The owner has asked to stop spending effort on validation of the rejected primitive design; no further such runs are required for this research phase.
