# Architecture Figures

## Figure 1 — Wiki Knowledge Graph

### 1a — Node Types & Edge Schema

```mermaid
flowchart TD
    TASK_T["📋 TASK\n─────────────────────\nAnalysis objective.\nFrontmatter: modality,\ncanonical_pipeline,\neval_weights\n─────────────────────\nExample: rna_clustering"]

    STAGE_T["⚙️ STAGE\n─────────────────────\nGeneric pipeline step,\nmodality-agnostic.\n─────────────────────\nExample: embed, cluster"]

    METHOD_T["🧠 METHOD\n─────────────────────\nAlgorithmic approach.\nLinks to concrete tools\nvia 'implements' edge.\n─────────────────────\nExample: linear_embedding"]

    TOOL_T["🔧 TOOL\n─────────────────────\nRunnable implementation.\nFrontmatter: params,\ndefault, requires_resources\n→ backend/tools/**/*.py\n─────────────────────\nExample: rna_embed_pca"]

    EVAL_T["📊 EVAL TOOL\n─────────────────────\nMetric computation.\nUsed to score and rank\nDAG paths.\n─────────────────────\nExample: eval_ari_nmi"]

    PKG_T["📦 PACKAGE\n─────────────────────\nSoftware dependency.\nMetadata only — not\ntraversed by planner.\n─────────────────────\nExample: scanpy"]

    RESOURCE_T["💾 RESOURCE\n─────────────────────\nExternal data / DBs.\nPresets with sizes;\ndownloaded on demand.\n─────────────────────\nExample: pyscenic_databases"]

    TASK_T -. "canonical_pipeline\n(ordered list)" .-> STAGE_T
    TASK_T -->|"evaluated_by"| EVAL_T
    STAGE_T -->|"rna / atac / multi\n(modality edge)"| METHOD_T
    METHOD_T -->|"implements"| TOOL_T
    TOOL_T -->|"package\n(metadata)"| PKG_T
    TOOL_T -. "requires_resources\n(triggers download flow)" .-> RESOURCE_T

    style TASK_T fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style STAGE_T fill:#f0fdf4,stroke:#22c55e,color:#14532d
    style METHOD_T fill:#fefce8,stroke:#eab308,color:#713f12
    style TOOL_T fill:#fdf4ff,stroke:#a855f7,color:#581c87
    style EVAL_T fill:#fff7ed,stroke:#f97316,color:#7c2d12
    style PKG_T fill:#f9fafb,stroke:#9ca3af,color:#374151
    style RESOURCE_T fill:#fef2f2,stroke:#ef4444,color:#7f1d1d
```

---

### 1b — All Current Nodes

```mermaid
flowchart LR

    subgraph TASKS["📋 Tasks  (18)"]
        direction TB
        subgraph RNA_T["RNA  (8)"]
            direction LR
            t1[rna_clustering]
            t2[rna_cell_type_annotation]
            t3[rna_batch_correction]
            t4[rna_differential_expression]
            t5[rna_differential_abundance]
            t6[rna_grn_inference]
            t7[rna_gene_programs]
            t8[rna_trajectory]
        end
        subgraph ATAC_T["ATAC  (7)"]
            direction LR
            t9[atac_clustering]
            t10[atac_cell_type_annotation]
            t11[atac_batch_correction]
            t12[atac_differential_accessibility]
            t13[atac_motif_analysis]
            t14[atac_peak_to_gene]
            t15[atac_grn_inference]
        end
        subgraph MULTI_T["Multi  (3)"]
            direction LR
            t16[multiomic_integration]
            t17[multi_cell_type_annotation]
            t18[multi_batch_correction]
            t19[multi_grn_inference]
        end
    end

    subgraph STAGES["⚙️ Stages  (17)"]
        direction LR
        s1[qc] 
        s2[normalize] 
        s3[feature_selection]
        s4[embed] 
        s5[batch_integration] 
        s6[cluster]
        s7[project] 
        s8[annotate] 
        s9[de]
        s10[da] 
        s11[peak_calling] 
        s12[peak_to_gene]
        s13[grn_inference] 
        s14[motif] 
        s15[gene_programs]
        s16[trajectory] 
        s17[differential_abundance]
    end

    subgraph METHODS["🧠 Methods  (35)"]
        direction TB
        subgraph QC_M["QC"]
            m1[basic_filter]
            m2[doublet_detection]
        end
        subgraph NORM_M["Normalize"]
            m3[library_size_normalization]
            m4[variance_stabilization]
        end
        subgraph FEAT_M["Feature"]
            m5[highly_variable_genes]
            m6[highly_variable_peaks]
        end
        subgraph EMBED_M["Embed"]
            m7[linear_embedding]
            m8[deep_generative_embedding]
            m9[spectral_embedding]
            m10[joint_embedding]
        end
        subgraph INT_M["Integration"]
            m11[embedding_correction]
            m12[graph_correction]
        end
        subgraph CLUST_M["Cluster"]
            m13[graph_based_clustering]
            m14[clustering_metrics]
        end
        subgraph PROJ_M["Project"]
            m15[nonlinear_projection]
        end
        subgraph ANN_M["Annotate"]
            m16[marker_based_annotation]
            m17[reference_based_annotation]
            m18[llm_based_annotation]
        end
        subgraph DE_M["DE"]
            m19[pseudobulk_de]
            m20[statistical_de]
            m21[mixed_model_de]
        end
        subgraph DA_M["DA"]
            m22[pseudobulk_da]
            m23[statistical_da]
            m24[neighborhood_da]
            m25[cluster_proportion_da]
        end
        subgraph PEAK_M["Peak"]
            m26[macs_peak_calling]
        end
        subgraph P2G_M["Peak2Gene"]
            m27[correlation_peak2gene]
        end
        subgraph MOTIF_M["Motif"]
            m28[motif_scanning]
            m29[motif_enrichment]
        end
        subgraph GRN_M["GRN"]
            m30[prior_knowledge_grn]
            m31[coexpression_grn]
        end
        subgraph PROG_M["Programs"]
            m32[nmf_programs]
            m33[mofa_programs]
        end
        subgraph TRAJ_M["Trajectory"]
            m34[diffusion_pseudotime]
        end
        subgraph BATCH_M["Batch"]
            m35[batch_metrics]
        end
    end

    subgraph TOOLS["🔧 Tools  (55)"]
        direction TB
        subgraph RNA_TOOLS["RNA Tools  (34)"]
            direction LR
            subgraph RQCA["QC"]
                rl1[rna_qc_basic]
                rl2[rna_qc_scrublet]
            end
            subgraph RNORM["Normalize"]
                rl3[rna_normalize_log1p]
                rl4[rna_normalize_sctransform]
                rl5[rna_normalize_scran]
            end
            subgraph RFEAT["Feature"]
                rl6[rna_feature_selection_scanpy_hvg]
                rl7[rna_feature_selection_seurat_v3]
                rl8[rna_feature_selection_cellranger]
            end
            subgraph REMB["Embed"]
                rl9[rna_embed_pca]
                rl10[rna_embed_scvi]
                rl11[rna_embed_scanvi]
                rl12[rna_embed_seurat_pca]
            end
            subgraph RINT["Integrate"]
                rl13[rna_batch_integration_harmony]
                rl14[rna_batch_integration_bbknn]
                rl15[rna_batch_integration_scanorama]
            end
            subgraph RCLUST["Cluster"]
                rl16[rna_cluster_leiden]
                rl17[rna_cluster_louvain]
            end
            subgraph RPROJ["Project"]
                rl18[rna_project_umap]
                rl19[rna_project_tsne]
            end
            subgraph RANN["Annotate"]
                rl20[rna_annotate_celltypist]
                rl21[rna_annotate_cellmarker]
                rl22[rna_annotate_gpt4]
                rl23[rna_annotate_azimuth]
                rl24[rna_annotate_singler]
                rl25[rna_annotate_scarches]
            end
            subgraph RDE["DE"]
                rl26[rna_de_wilcoxon]
                rl27[rna_de_ttest]
                rl28[rna_de_pseudobulk]
                rl29[rna_de_edger]
                rl30[rna_de_mast]
            end
            subgraph RGRN["GRN"]
                rl31[rna_grn_decoupler]
                rl32[rna_grn_grnboost2]
                rl33[rna_grn_pyscenic]
            end
        end
        subgraph ATAC_TOOLS["ATAC Tools  (15)"]
            direction LR
            subgraph AQCA["QC"]
                al1[atac_qc_basic]
                al2[atac_qc_fragment_size]
            end
            subgraph AFEAT["Feature"]
                al3[atac_feature_selection_peaks]
            end
            subgraph AEMB["Embed"]
                al4[atac_embed_lsi]
            end
            subgraph AINT["Integrate"]
                al5[atac_batch_integration_harmony]
            end
            subgraph ACLUST["Cluster"]
                al6[atac_cluster_leiden]
                al7[atac_cluster_louvain]
            end
            subgraph APROJ["Project"]
                al8[atac_project_umap]
            end
            subgraph AANN["Annotate"]
                al9[atac_annotate_gene_activity]
                al10[atac_annotate_marker_peaks]
            end
            subgraph APEAK["Peak Calling"]
                al11[atac_peak_calling_macs2]
                al12[atac_peak_calling_macs3]
            end
            subgraph ADA["DA"]
                al13[atac_da_wilcoxon]
            end
            subgraph AP2G["Peak2Gene"]
                al14[atac_peak_to_gene_correlation]
            end
            subgraph AMOTIF["Motif"]
                al15[atac_motif_enrichment]
            end
        end
        subgraph MULTI_TOOLS["Multi Tools  (4)"]
            direction LR
            ml1[multi_qc_intersect]
            ml2[multi_embed_multivi]
            ml3[multi_embed_wnn]
            ml4[multi_embed_mofa]
        end
        subgraph EVAL_TOOLS["Eval Tools  (4)"]
            direction LR
            ev1[eval_ari_nmi]
            ev2[eval_silhouette]
            ev3[eval_ilisi_clisi]
            ev4[eval_kbet]
        end
    end

    subgraph PACKAGES["📦 Packages  (20)"]
        direction LR
        p1[scanpy] 
        p2[scvi_tools] 
        p3[leidenalg]
        p4[celltypist] 
        p5[harmonypy] 
        p6[bbknn]
        p7[scanorama] 
        p8[sklearn] 
        p9[snapatac2]
        p10[macs2] 
        p11[macs3] 
        p12[muon]
        p13[pyscenic] 
        p14[openai] 
        p15[pydeseq2]
        p16[decoupler] 
        p17[scib_metrics] 
        p18[milopy]
        p19[diffxpy] 
        p20[statsmodels]
    end

    subgraph RESOURCES["💾 Resources  (3)"]
        direction LR
        r1[pyscenic_databases]
        r2[pbmc_3k]
        r3[pbmc_multiome_10k]
    end

    TASKS -->|"canonical_pipeline\n→ ordered stage list"| STAGES
    TASKS -->|"evaluated_by"| TOOLS
    STAGES -->|"rna / atac / multi\nedge"| METHODS
    METHODS -->|"implements"| TOOLS
    TOOLS -->|"package"| PACKAGES
    TOOLS -.->|"requires_resources"| RESOURCES

    style TASKS fill:#dbeafe,stroke:#3b82f6
    style STAGES fill:#f0fdf4,stroke:#22c55e
    style METHODS fill:#fefce8,stroke:#eab308
    style TOOLS fill:#fdf4ff,stroke:#a855f7
    style PACKAGES fill:#f9fafb,stroke:#9ca3af
    style RESOURCES fill:#fef2f2,stroke:#ef4444
    style RNA_T fill:#eff6ff,stroke:#93c5fd
    style ATAC_T fill:#eff6ff,stroke:#93c5fd
    style MULTI_T fill:#eff6ff,stroke:#93c5fd
    style RNA_TOOLS fill:#faf5ff,stroke:#d8b4fe
    style ATAC_TOOLS fill:#faf5ff,stroke:#d8b4fe
    style MULTI_TOOLS fill:#faf5ff,stroke:#d8b4fe
    style EVAL_TOOLS fill:#fff7ed,stroke:#fdba74
```

---

## Figure 2 — Agent System Flow

```mermaid
flowchart TD
    USER(["👤 User Message\n\"Find the best clustering\nworkflow, then report\nARI/NMI\""])

    subgraph FRONTEND["Frontend  (frontend/server.py)"]
        HTTP["HTTP POST /message"]
    end

    subgraph DISPATCHER["Session Dispatcher  (agents/session_dispatcher.py)"]
        ROUTER["SessionRouter\n─────────────\nClassify: task vs\ndirect_response\n(LLM + JSON schema)"]
        STATE["SessionStateStore\n─────────────\nactive_h5ad_path\nactive_cluster_key\nactive_embedding_key\nlast_decision / result\nhistory"]
    end

    subgraph CONSULTANT["Tool Consultant  (agents/tool_consultant.py)"]
        TC_LOOP["ToolCallingAgentRunner\nmax_iterations: 25\nmax_tool_calls: 40"]
        WIKI_TOOLS["Wiki Tools\n─────────────\nwiki_query_tasks()\nwiki_fetch_task_graph()\nwiki_graph_query()\nwiki_fetch_resource()"]
        DECISION["TOOL_DECISION JSON\n─────────────\ndag_plan / implementation_plan\n/ research_brief\n+ objective_name"]
    end

    subgraph DAGEXEC["DAG Executor  (agents/dag_executor.py)"]
        PATHS["Enumerate Paths\nCartesian product of\nall layer variants"]
        EXEC["Execute Each Path\nsequential tool chain\nper path"]
        CACHE["Step Cache\nhit → skip re-run\n(sha256 keyed)"]
        EVAL["Evaluate All Paths\nARI, NMI, Silhouette\nper completed path"]
        RANK["Rank & Select Best\nobjective scoring\n0.4·ARI + 0.4·NMI\n+ 0.2·ASW"]
        ARTIFACTS["ArtifactManifest\nbest / result /\nephemeral / metadata"]
    end

    subgraph BACKEND["Backend Tools  (backend/tools/)"]
        REG["Tool Registry\nauto-discovery of\nbackend/tools/**/*.py"]
        ADAPT["Adapter Pattern\nload h5ad → run() → write h5ad\nexecutor-managed I/O"]
        RNATOOLS["RNA Tools\nqc · normalize · hvg\npca · scvi · leiden\numap · celltypist · …"]
        ATACTOOLS["ATAC Tools\nmacs3 · lsi · leiden\ncorrelation · motif · …"]
        MULTITOOLS["Multi Tools\nintersect · multivi\nwnn · mofa · …"]
        EVALTOOLS["Eval Tools\nari_nmi · silhouette\nilisi_clisi · kbet"]
    end

    subgraph CODER["Coder Agent  (agents/coder.py)  — optional"]
        GEN["Generate Script\nfrom implementation_plan\n+ dag best_path inputs"]
        FIX["Fix Loop\nup to max_fix_step\nrounds of LLM repair"]
    end

    subgraph SUMMARIZER["Result Summarizer  (agents/result_summarizer.py)"]
        SUM["LLM synthesis\nraw_results + decision\n→ user-facing message\n+ figure paths"]
    end

    USER --> HTTP --> ROUTER
    ROUTER -->|"task"| TC_LOOP
    ROUTER -->|"direct_response"| STATE

    TC_LOOP <-->|"tool calls"| WIKI_TOOLS
    TC_LOOP --> DECISION

    DECISION -->|"dag_plan"| PATHS
    DECISION -->|"implementation_plan\ndepends_on_dag: true"| PATHS

    PATHS --> EXEC
    EXEC <-->|"cache hit/miss"| CACHE
    EXEC <-->|"run tool"| ADAPT
    ADAPT --> REG
    REG --> RNATOOLS
    REG --> ATACTOOLS
    REG --> MULTITOOLS
    REG --> EVALTOOLS

    EXEC --> EVAL
    EVAL --> RANK
    RANK --> ARTIFACTS

    ARTIFACTS -->|"best_path inputs"| GEN
    GEN --> FIX

    RANK --> SUM
    FIX --> SUM
    SUM --> STATE
    STATE --> USER

    style FRONTEND fill:#dbeafe,stroke:#3b82f6
    style CONSULTANT fill:#fefce8,stroke:#eab308
    style DAGEXEC fill:#f0fdf4,stroke:#22c55e
    style BACKEND fill:#fdf4ff,stroke:#a855f7
    style CODER fill:#fff7ed,stroke:#f97316
    style SUMMARIZER fill:#fef2f2,stroke:#ef4444
    style DISPATCHER fill:#f9fafb,stroke:#9ca3af
```

---

## Figure 3 — Example: "Find the best clustering workflow, then report ARI/NMI"

```mermaid
sequenceDiagram
    actor User
    participant Router as SessionRouter
    participant Consultant as ToolConsultant
    participant Wiki as Wiki Tools
    participant DAG as DagExecutor
    participant Tools as Backend Tools
    participant Eval as Eval Tools
    participant Coder as CoderAgent
    participant Summary as ResultSummarizer

    User->>Router: "Find the best clustering workflow,<br/>then report ARI/NMI"
    Router->>Router: Classify → task

    Router->>Consultant: decide(user_message, session_state)

    Note over Consultant,Wiki: Round 1 — find task
    Consultant->>Wiki: wiki_query_tasks(modality="rna")
    Wiki-->>Consultant: [{id: "rna_clustering", canonical_pipeline: [qc, normalize,<br/>feature_selection, embed, cluster, project, annotate]}]

    Note over Consultant,Wiki: Round 2 — fetch complete subgraph
    Consultant->>Wiki: wiki_fetch_task_graph(task_id="rna_clustering", modality="rna")
    Wiki-->>Consultant: {stages: [{id:"qc", methods:[{tools:[rna_qc_basic]}]},<br/>{id:"embed", methods:[{tools:[rna_embed_pca, rna_embed_scvi]}]},<br/>{id:"cluster", methods:[{tools:[rna_cluster_leiden, rna_cluster_louvain]}]},<br/>...]},<br/>eval_tools: [{id:"eval_ari_nmi", params:{...}}]}

    Note over Consultant: Plan: vary embed × cluster → 4 paths<br/>Add variants at embed (pca, scvi) and cluster (leiden, louvain)
    Consultant-->>Router: TOOL_DECISION {dag_plan: {layers: [<br/>  L0: qc [basic],<br/>  L1: normalize [log1p],<br/>  L2: feature_selection [hvg],<br/>  L3: embed [pca, scvi],       ← 2 variants<br/>  L4: cluster [leiden, louvain], ← 2 variants<br/>  L5: project [umap],<br/>  L6: annotate [celltypist]<br/>], evaluation: {metrics:[ari,nmi,silhouette],<br/>  embedding_key:"$L3.embedding_key",<br/>  cluster_key:"$L4.cluster_key"}}}

    Router->>DAG: execute(dag_plan)

    Note over DAG: Enumerate 4 paths:<br/>Path 0: pca + leiden<br/>Path 1: pca + louvain<br/>Path 2: scvi + leiden<br/>Path 3: scvi + louvain

    loop For each of 4 paths (parallel where cache allows)
        DAG->>Tools: rna_qc_basic(adata, min_genes=200, max_pct_mito=20)
        Tools-->>DAG: filtered adata (cache hit on shared prefix)
        DAG->>Tools: rna_normalize_log1p(adata)
        Tools-->>DAG: normalized adata (cache hit)
        DAG->>Tools: rna_feature_selection_hvg(adata, n_top_genes=2000)
        Tools-->>DAG: hvg adata (cache hit)
        DAG->>Tools: rna_embed_pca / rna_embed_scvi (varies per path)
        Tools-->>DAG: adata + obsm["X_pca"] or obsm["X_scvi"]
        DAG->>Tools: rna_cluster_leiden / rna_cluster_louvain (varies per path)
        Tools-->>DAG: adata + obs["leiden"] or obs["louvain"]
        DAG->>Tools: rna_project_umap(adata)
        Tools-->>DAG: adata + obsm["X_umap"]
        DAG->>Tools: rna_annotate_celltypist(adata)
        Tools-->>DAG: adata + obs["cell_type"]
        DAG->>Eval: eval_ari_nmi(adata, cluster_key="leiden",<br/>embedding_key="X_pca", label_key="cell_type")
        Eval-->>DAG: {ari: 0.82, nmi: 0.79, silhouette: 0.61}
    end

    Note over DAG: Rank by objective: 0.4·ARI + 0.4·NMI + 0.2·ASW<br/>Best: scvi + leiden  (score 0.84)<br/>2nd:  pca + leiden   (score 0.76)<br/>3rd:  scvi + louvain (score 0.71)<br/>4th:  pca + louvain  (score 0.68)

    DAG-->>Router: {best_path: "scvi+leiden",<br/>metrics: {ari:0.87, nmi:0.83, silhouette:0.65},<br/>comparison_table: [...all 4 paths...],<br/>artifacts: {output_h5ad, umap_plot}}

    Router->>Summary: summarize(decision, dag_result)
    Summary-->>User: "The best clustering workflow is scvi + leiden<br/>(ARI 0.87 · NMI 0.83 · Silhouette 0.65).<br/>Compared to 3 other paths:<br/>| Method       | ARI  | NMI  | ASW  |<br/>|scvi+leiden   | 0.87 | 0.83 | 0.65 |  ← best<br/>|pca+leiden    | 0.81 | 0.76 | 0.58 |<br/>|scvi+louvain  | 0.75 | 0.70 | 0.54 |<br/>|pca+louvain   | 0.68 | 0.65 | 0.49 |<br/>[UMAP figure attached]"
```
