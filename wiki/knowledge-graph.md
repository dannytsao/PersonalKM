# Knowledge Graph

Last updated: 2026-06-28T18:13:46.853974

> Mermaid flowchart (TD layout) — click a node to open the page. Entities are blue, concepts are orange. Edges are wikilinks. Zoom: scroll, Pan: drag background.

```mermaid
%%{init: {'flowchart': {'useMaxWidth': false, 'htmlLabels': true, 'curve': 'basis', 'padding': 15}}}%%
flowchart TD
    classDef entity fill:#e1f5fe,stroke:#01579b,stroke-width:2px,cursor:pointer;
    classDef concept fill:#fff3e0,stroke:#e65100,stroke-width:1px,cursor:pointer;

    subgraph Entities
        claude_code["Claude Code"]
        click claude_code "entities/claude-code.md" "Open Claude Code"
        class claude_code entity
        glm_5_2["GLM 5.2"]
        click glm_5_2 "entities/glm-5-2.md" "Open GLM 5.2"
        class glm_5_2 entity
    end

    subgraph Concepts
    end

```

## Canonical Entities

- [[claude-code|Claude Code]]
- [[glm-5-2|GLM 5.2]]

---
Total pages: 2 | Edges: 0