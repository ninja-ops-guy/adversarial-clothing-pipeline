# P1 Capture Naming Convention

Deterministic filename grammar. Every capture filename parses back to full
trial metadata with no database; the session manifest only stores filenames
plus SHA-256.

## Grammar

```
P1_<session>_<sku>_<distance>_<yaw>_<pitch>_<light>_<pose>_<rep>.<ext>
```

| Field | Format | Example |
|---|---|---|
| `session` | `S` + zero-padded session sequence | `S001` |
| `sku` | garment SKU, `-` in SKU replaced by `_` | `RAC_SKU_CTRL_001` |
| `distance` | `d` + distance in cm, zero-padded 4 | `d0100` (1.0 m), `d0500` (5.0 m) |
| `yaw` | `y` + signed degrees | `ym45`, `yp00`, `yp45` |
| `pitch` | `p` + signed degrees | `pp00` |
| `light` | lighting variant id | `L1` |
| `pose` | pose id, lowercase | `standing` |
| `rep` | `r` + repetition, zero-padded 2 | `r01` |
| `ext` | `png` or `jpg` (export), `raw` kept alongside under the same stem |

## Regex

```regex
^P1_(?P<session>S\d{3})_(?P<sku>[A-Z0-9_]+)_(?P<distance>d\d{4})_(?P<yaw>y[mp]\d{2})_(?P<pitch>p[mp]\d{2})_(?P<light>L\d+)_(?P<pose>[a-z0-9]+)_(?P<rep>r\d{2})\.(?P<ext>png|jpg)$
```

## Example

```
P1_S001_RAC_SKU_CAND_003_d0300_ym45_pp00_L1_standing_r02.png
```

= session 1, candidate SKU `RAC-SKU-CAND-003`, 3.0 m, yaw -45 deg, pitch 0,
lighting L1, standing, repetition 2.

## Pairing rule

A matched trial is the pair of filenames identical in every field except
`sku` (one control SKU, one candidate SKU) and `rep`. The `trial_id` is
derived, not stored: `RAC-P1-T-<session>-<distance>-<yaw>-<pitch>-<light>-<pose>-<rep>`.

## Rules

- Filenames are written at capture time and never renamed; a misnamed file
  is quarantined, not fixed in place.
- The parser must round-trip: parse(compose(meta)) == meta for every
  capture in the session manifest.
