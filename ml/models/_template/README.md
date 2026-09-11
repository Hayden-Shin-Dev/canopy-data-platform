# Model Template

Copy this directory when introducing a new ML prediction task.

- `training/`: model training code
- `inference/`: runtime inference code
- `evaluation/`: offline evaluation
- `features/`: task-specific feature logic
- `configs/`: model and training configuration
- `tests/`: model-specific tests

Reusable ML logic belongs in `ml/shared/`.
