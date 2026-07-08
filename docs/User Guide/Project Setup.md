# Project Setup

To start a new project, create an empty folder with a `config.yaml` file.

When you run Frame Extractor on this folder, Junip3R creates the remaining project structure automatically.

## Minimum required `config.yaml`

At minimum, define `instance_types`. Each instance type needs:

- `name`: unique instance type name
- `points`: list of point names for that instance type

```yaml
instance_types:
- name: mouse_top
  points:
  - nose
  - headcentre
  - neck
  - earl
  ...
```

## Optional fields
See [`docs/Examples/advanced_config.yaml`](../Examples/advanced_config.yaml)) for more details

### Per instance type

- `bounding_box_type`: `automatic` or `manual` (default is `manual`)
  - `automatic`: box is computed tightly around points
  - `manual`: user places the box manually
- `skeleton`: list of point pairs, for example `[[nose, headcentre], [headcentre, neck]]`
- `colors`: list of hex colors for points (same order as `points`)
- `box_color`: hex color for the bounding box
- `skeleton_color`: hex color for skeleton lines

### Project-wide

- `instances`: ordered list of expected instance type names
  - Used by the UI to auto-select the next type while labelling

## Example configs

- Minimal example: [`docs/Examples/minimal_config.yaml`](../Examples/minimal_config.yaml)
- Advanced example: [`docs/Examples/advanced_config.yaml`](../Examples/advanced_config.yaml)
