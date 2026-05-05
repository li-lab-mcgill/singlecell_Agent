---
type: tool
id: atac_peak_calling_macs2
stage: peak_calling
modality: atac
backend: backend/tools/atac/peak_calling/macs2.py
---

Calls peaks using MACS2. Same workflow as `atac_peak_macs3` but uses the MACS2 binary. Use only when reproducing older analyses that specified MACS2.

Key parameters: same as `atac_peak_macs3`.

MACS2 uses `macs2` binary; MACS3 uses `macs3` binary. Output format is identical (narrowPeak). Minor differences in peak boundary detection between versions.

Package: [[packages/macs2]]
Method: [[methods/macs_peak_calling]]
