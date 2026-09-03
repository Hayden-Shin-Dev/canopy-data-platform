# AI-Hub official runtime reproduction

Branch: `feature/mobility-multimodal-v4`

## Runtime check (2026-09-03)

- Docker image: `nia56:latest` loaded successfully.
- Image ID: `sha256:79e0dca74cafa291d510100554aba21f1e7eadbbc5949458ca0a888ede4b26a5`.
- Container Python: 3.9.15.
- PyTorch: 1.9.1 (CUDA 11.1 build).
- CPU runtime: PASS.
- GPU runtime: FAIL. `nvidia-container-cli` reports that the WSL environment has no adapters.
- Checkpoint: `/ml/last.chk` deserialized on CPU; final layer is `(11, 2190)` and produces 11 logits.
- Checkpoint deserialize latency: approximately 463 ms.

## Official contract

The source uses `PER_SECTION=1` and `PER_MIN=60`. GPS and BTS are aggregated
in 5-second bins and repeated over 60 timesteps, so the observation is 60 s.

- Input tensor: `(340, 60)`
- Output: 11 logits
- Required raw modalities: GPS, IMU, AP/Wi-Fi, BTS/cell
- The source label comments and the 11-logit checkpoint do not provide a
  verified Canopy 5-class mapping; mapping remains unclaimed.

## Input and inference status

The local `186.교통수단판별 데이터/01-1.정식개방데이터/Validation` tree contains
GPS and labels only. It does not contain the official `1.AP`, `2.BTS`, `3.GPS`,
and `4.IMU` raw tree. AP/BTS/IMU values were not zero-filled or fabricated.

Therefore image/CPU/checkpoint smoke is PASS, while official preprocessing,
forward inference, prediction latency, and modality ablation are BLOCKED until
the missing raw sensor files are supplied in the official layout. The current
result is recorded in `reports/mobility_v4/OFFICIAL_MODEL_SMOKE.json`.

```powershell
python -m scripts.run_aihub_official_smoke `
  --official-root "C:\path\to\official\20231207" `
  --data-root "C:\path\to\raw\Validation" `
  --image nia56:latest `
  --output reports/mobility_v4/OFFICIAL_MODEL_SMOKE.json
```

No V3 production code, selector, or artifact was modified.
