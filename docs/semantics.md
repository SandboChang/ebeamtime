# Estimation Semantics

- Polygon area is accumulated per raw flattened polygon instance. Overlaps are
  counted separately.
- GDS coordinates are extracted by `gdsdiff` onto the file precision grid; area
  converts from twice-area in database units to square micrometres.
- Beam-on seconds equal `area_um2 * dose_uC_cm2 * 1e-5 / beam_current_nA`.
- An ambiguous multi-top GDS requires an explicit top cell.
- Stage fields may come from indicator polygons or deterministic tiling by the
  maximum write-field size. A polygon exactly ending on a tile boundary does
  not create a field on the far side.
- `auto` selects an available GPU only at the configured size threshold and
  falls back to CPU on runtime failure unless `require_gpu` is true.
