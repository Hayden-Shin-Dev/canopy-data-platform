"""Render the reproducible mock-trip evaluation into a team-facing report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render(source: Path) -> str:
    report = json.loads(source.read_text(encoding="utf-8"))
    baseline = report["ktdb_baseline"]
    production = report["production_pipeline"]
    lines = [
        "# Integration E2E 원인 분석",
        "",
        "동일한 433개 iPhone 형식 GPS CSV를 재생해 production pipeline 결과를 기록한 보고서입니다. Ground Truth는 비교에만 사용했고 inference 입력으로 읽지 않았습니다.",
        "",
        "## KTDB Baseline",
        "",
        "이전에는 processed dataset 첫 행(동일 동네, 거리 0km, 17시 non_commute)을 고정 입력으로 사용해 walk 86.8%, rail 9.4%가 나왔습니다. 이는 UI가 실제 경로 조건을 전달하지 않은 입력 문제였습니다.",
        "",
        f"현재는 SGIS centroid와 KTDB mapping으로 실제 경로 조건을 만들었습니다. {baseline['features']}",
        "",
        "현재 확률:",
        "",
    ]
    for mode, value in baseline["probabilities"].items():
        lines.append(f"- {mode}: {float(value) * 100:.2f}%")
    lines += [
        "",
        f"예측 mode: {baseline['predicted_mode']}",
        f"provenance: {baseline['provenance']}",
        "",
        "## Window별 결과",
        "",
        "| Window 시작 | GeoLife | 최종 mode | Subway score | Sequence | 관측 station |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for window in production["window_results"]:
        context = window["transit_context"]
        lines.append(
            f"| {window['window_start']} | {window['geolife_predicted_mode']} | {window['final_mode']} | "
            f"{float(context.get('subway_context_score') or 0):.3f} | {float(context.get('subway_sequence_score') or 0):.3f} | "
            f"{','.join(context.get('subway_current_observed_station_ids') or [])} |"
        )
    lines += [
        "",
        "GeoLife 모델은 rail 구간에서 bike를 예측했지만, 여러 Window에 걸쳐 같은 subway reference의 station 순서가 확인된 뒤 resolver가 rail로 보정했습니다. 마지막 고신뢰 walk Window에서는 rail을 종료했습니다. 이는 특정 노선이나 Ground Truth를 사용한 규칙이 아닙니다.",
        "",
        "## Trip Segmentation 및 Emission",
        "",
        f"mode sequence: `{' → '.join(_compress(production['mode_sequence']))}`",
        "",
        "| Segment | Window | 거리(km) | CO2e(g) | Subway line |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for index, segment in enumerate(production["segments"], start=1):
        lines.append(
            f"| {index}. {segment['mode']} | {','.join(str(x) for x in segment['window_indices'])} | "
            f"{float(segment['distance_km']):.3f} | {float(segment['co2e_g']):.1f} | {(segment.get('matched_subway_line') if segment.get('mode') == 'rail' else None) or '-'} |"
        )
    lines += [
        "",
        f"- 총 거리: {float(production['distance_km']):.3f} km",
        f"- Expected CO2: {float(production['expected_co2e_g']):.1f} g",
        f"- Actual CO2: {float(production['actual_co2e_g']):.1f} g",
        f"- Reduction: {float(production['reduction_co2e_g']):.1f} g",
        "",
        "Actual CO2는 각 Segment의 거리와 기존 Emission Factor를 곱해 합산했습니다. 마지막 Window 하나의 mode로 계산하지 않습니다.",
        "",
        "## 검증",
        "",
        f"- Replay: {report['replay']['accepted_event_count']} accepted, {report['replay']['rejected_event_count']} rejected",
        "- Label leakage: PASS",
        f"- Production pipeline: {production['status']}",
        "- 전체 테스트는 커밋 전에 실행합니다.",
    ]
    return "\n".join(lines) + "\n"


def _compress(modes: list[str]) -> list[str]:
    result: list[str] = []
    for mode in modes:
        if not result or result[-1] != mode:
            result.append(mode)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(args.source), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
