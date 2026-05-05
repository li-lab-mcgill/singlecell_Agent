---
type: method
id: motif_enrichment
label: TF Motif Enrichment in Peaks
---

Motif enrichment tests whether a set of peaks (e.g., DA peaks) is significantly enriched for TF binding motifs compared to a background set of peaks. This identifies TFs that may regulate the differential accessibility.

Standard approach: for each motif in JASPAR or HOCOMOCO, count how many peaks in the foreground contain the motif vs. the background, then use a Fisher's exact test or binomial test.

Tools:
- **SnapATAC2 `snap.tl.motif_enrichment()`**: built-in; uses Fisher's test against a GC-content-matched background
- **Homer (command-line)**: `findMotifsGenome.pl`; widely used; requires Perl

Background selection is critical: use GC-content-matched background peaks (same GC distribution as foreground) to avoid false positives driven by AT/GC-rich regions.

Output: motif × statistics table with enrichment score, p-value, and adjusted p-value. Top enriched motifs are candidate TF regulators.

Edges:
- [[tools/atac_motif_enrichment]] implements
