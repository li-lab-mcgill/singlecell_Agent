---
paper_id: cellphenox_2025
title: "CellPhenoX: An eXplainable Cell-specific machine learning method to predict clinical Phenotypes using single-cell multi-omics."
doi: "10.1101/2025.01.24.634132"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11838219/"
source_ids: {doc_id: "pmc:11838219", pmid: "39975336", pmcid: "11838219", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_abundance"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine how single-cell disease-control studies statistically test cell-type/state abundance and avoid confounding molecular differential state claims with compositional shifts and donor/batch covariates."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
CellPhenoX is an explainable machine learning framework that converts single-cell measurements into neighborhood abundance features, predicts sample-level clinical phenotypes, and maps SHAP-derived contributions back to cell-specific scores. The method is intended to identify disease-associated cell populations, phenotypic gradients, and covariate or interaction effects in single-cell multi-omics studies.

## Hypothesis framed
Cell-level neighborhood abundance patterns in single-cell multi-omics data can be used with covariate-adjusted classification models and SHAP explanations to identify cell-specific phenotypes associated with clinical outcomes.

## Questions answered
- Can neighborhood abundance features from single-cell data predict binary disease-control and multi-class clinical phenotypes while incorporating covariates and interaction terms?
- Can SHAP-derived cell-specific scores identify clinically relevant cell populations associated with disease severity or inflammation?
- Can CellPhenoX detect cell populations influenced by interaction effects such as sex- or age-related effects?

## Key findings
CellPhenoX identified clinically relevant cell phenotypes across simulations and real single-cell datasets. In COVID-19 data, it detected an activated monocyte phenotype whose expansion correlated with disease severity after adjustment for covariates and interaction effects. In ulcerative colitis data, it uncovered an inflammation-associated gradient in fibroblasts and detected cell populations influenced by sex- and age-related interaction effects.

## Methods used
Neighborhood abundance matrix construction from single-cell measurements; dimensionality reduction of neighborhood abundance features; classification models for clinical phenotype prediction; explicit inclusion of covariates and optional interaction terms; nested cross-validation; hold-out validation; SHAP value calculation; aggregation of SHAP contributions into cell-specific scores; visualization of scores on low-dimensional embeddings such as UMAP.

## Method and dataset
The method was evaluated on simulations and real single-cell datasets including binary disease-control comparisons and multi-class clinical phenotype studies. It represents each sample by neighborhood-level cell abundance features, learns latent features by dimensionality reduction, predicts clinical labels using classification models with covariates and interaction terms, and assumes that disease-associated cellular phenotypes can be captured as predictive neighborhood abundance patterns across samples.

## Limitations
The summary does not report extensive author-stated limitations. Potential limitations described include dependence on single-cell data quality and scale, sensitivity to neighborhood construction, dimensionality reduction, and classifier choice, need for careful covariate handling and validation to reduce overfitting, and the requirement for downstream biological validation because observational associations do not establish causality.

## Evidence pattern
Entity definition: cell populations or states are represented by neighborhoods and assigned SHAP-derived cell-specific scores. Comparison design: simulations, binary disease-control analyses, and multi-class studies. Statistical unit: samples or donors represented by neighborhood abundance features for clinical phenotype prediction. Metric: predictive model performance and SHAP contribution scores; no standard abundance-test log-fold changes, p-values, credible intervals, or FDR are reported in the summary. Covariates: models explicitly incorporate covariates and optional interaction terms, including sex- and age-related effects. Validation: nested cross-validation and hold-out validation. Analysis used: neighborhood abundance modeling, dimensionality reduction, classification, SHAP explanation, and UMAP mapping.

## Extends or contradicts
Extends neighborhood-based and differential abundance concepts by combining sample-level clinical phenotype prediction, covariate and interaction modeling, and SHAP-based cell-specific interpretability. The summary does not identify a direct contradiction of prior work.

## Boundary conditions
Works when: Works for single-cell datasets with multiple samples or donors where clinical phenotypes such as disease status, severity, treatment response, or multi-class labels are available, and where covariates or interaction terms can be included in sample-level predictive models. It is applicable when cell phenotypes can be represented by neighborhood abundance patterns and validated through nested cross-validation or hold-out samples.
Fails when: May be unreliable when there are too few samples to train and validate sample-level classifiers, when neighborhood construction or dimensionality reduction fails to capture biologically meaningful populations, when covariates or batch effects are unmeasured or poorly modeled, or when the research question requires formal compositional abundance inference with log-fold changes, p-values, credible intervals, or FDR rather than predictive SHAP-derived scores.
