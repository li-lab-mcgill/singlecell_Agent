---
type: package
id: macs2
version: ">=2.2"
citation: Zhang et al. 2008 Genome Biology
---

MACS2 is the previous major version of MACS for peak calling. It is Python 2/3 compatible and still widely used in published workflows.

Install: `pip install macs2`

Use MACS3 for new analyses. MACS2 is included here only for reproducibility of older pipelines. The CLI interface is identical to MACS3 with the same key parameters:
- `--format BEDPE --nomodel --shift -100 --extsize 200 --qvalue 0.05`

Key difference: MACS2 uses a slightly different background lambda model. Results from MACS2 and MACS3 on the same data will have minor differences in peak boundaries and significance values.

If a published analysis specifies MACS2, use MACS2 to reproduce results. Otherwise default to MACS3.
