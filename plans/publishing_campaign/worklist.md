# Publishing Campaign Worklist

The authoritative sequence is shared with the sibling `gdsdiff` campaign.
`ebeamtime` hardening and publication starts after the `gdsdiff` release gate is
green, and production publication requires `gdsdiff==0.1.0` on PyPI.

- Reproducible `uv` environment: complete locally; production lock waits for stable `gdsdiff`
- Backend contract and CUDA preparation hardening: complete
- Schema and installed-package qualification: complete
- Hosted CI and Trusted Publishing workflows: complete; account configuration pending
- TestPyPI candidate: pending external publisher setup
- Production PyPI `0.1.0`: pending
