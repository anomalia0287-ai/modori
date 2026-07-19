from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GALLERY = ROOT / ".visual-qa/research-flow"
DEFAULT_PACKET = ROOT / ".visual-qa/research-flow-mode-a"
DEFAULT_SOURCE_MANIFEST = ROOT / "tests/fixtures/research_flow_visual_states.json"


class ReviewPacketError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _parse_hex(value: str) -> tuple[float, float, float, float]:
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?", value):
        raise ReviewPacketError(f"unsupported color literal: {value}")
    digits = value[1:]
    channels = [int(digits[index : index + 2], 16) / 255.0 for index in (0, 2, 4)]
    alpha = int(digits[6:8], 16) / 255.0 if len(digits) == 8 else 1.0
    return channels[0], channels[1], channels[2], alpha


def composite_rgba(
    foreground: tuple[float, float, float, float],
    background: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    if background[3] < 1.0:
        raise ReviewPacketError("contrast backgrounds must be opaque after composition")
    alpha = foreground[3]
    return (
        foreground[0] * alpha + background[0] * (1.0 - alpha),
        foreground[1] * alpha + background[1] * (1.0 - alpha),
        foreground[2] * alpha + background[2] * (1.0 - alpha),
        1.0,
    )


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _luminance(color: tuple[float, float, float, float]) -> float:
    if color[3] < 1.0:
        raise ReviewPacketError("relative luminance requires an opaque color")
    return (
        0.2126 * _linear(color[0])
        + 0.7152 * _linear(color[1])
        + 0.0722 * _linear(color[2])
    )


def contrast_ratio(foreground: str, background: str) -> float:
    background_rgba = _parse_hex(background)
    foreground_rgba = _parse_hex(foreground)
    if foreground_rgba[3] < 1.0:
        foreground_rgba = composite_rgba(foreground_rgba, background_rgba)
    foreground_luminance = _luminance(foreground_rgba)
    background_luminance = _luminance(background_rgba)
    lighter = max(foreground_luminance, background_luminance)
    darker = min(foreground_luminance, background_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def passes_contrast(ratio: float, threshold: float) -> bool:
    return ratio >= threshold


def _theme_color_expressions(theme_path: Path) -> dict[str, str]:
    declaration = re.compile(r"^\s*readonly property color (\w+):\s*(.*?)\s*$")
    lines = theme_path.read_text(encoding="utf-8").splitlines()
    expressions: dict[str, str] = {}
    index = 0
    while index < len(lines):
        match = declaration.match(lines[index])
        if match is None:
            index += 1
            continue
        name, expression = match.groups()
        parenthesis_depth = expression.count("(") - expression.count(")")
        while parenthesis_depth > 0 and index + 1 < len(lines):
            index += 1
            continuation = lines[index].strip()
            expression = f"{expression} {continuation}"
            parenthesis_depth += continuation.count("(") - continuation.count(")")
        expressions[name] = " ".join(expression.split())
        index += 1
    return expressions


def _format_rgba(color: tuple[float, float, float, float]) -> str:
    channels = tuple(
        max(0, min(255, int(channel * 255.0 + 0.5))) for channel in color
    )
    red, green, blue, alpha = channels
    suffix = f"{alpha:02X}" if alpha < 255 else ""
    return f"#{red:02X}{green:02X}{blue:02X}{suffix}"


def _resolve_theme_color(
    name: str,
    expressions: Mapping[str, str],
    *,
    stack: tuple[str, ...] = (),
) -> str:
    if name in stack:
        raise ReviewPacketError(
            f"cyclic theme color alias: {' -> '.join((*stack, name))}"
        )
    expression = expressions.get(name)
    if expression is None:
        raise ReviewPacketError(f"unknown theme color token: {name}")
    literal = re.fullmatch(r'"(#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?)"', expression)
    if literal:
        return literal.group(1).upper()
    alias = re.fullmatch(r"[A-Za-z_]\w*", expression)
    if alias:
        return _resolve_theme_color(alias.group(0), expressions, stack=(*stack, name))
    rgba = re.fullmatch(
        r"Qt\.rgba\(\s*([A-Za-z_]\w*)\.r\s*,\s*\1\.g\s*,\s*\1\.b\s*,"
        r"\s*(0(?:\.\d+)?|1(?:\.0+)?)\s*\)",
        expression,
    )
    if rgba:
        base_name, alpha_text = rgba.groups()
        base = _parse_hex(
            _resolve_theme_color(base_name, expressions, stack=(*stack, name))
        )
        return _format_rgba((base[0], base[1], base[2], float(alpha_text)))
    transform = re.fullmatch(
        r"Qt\.(lighter|darker)\(\s*([A-Za-z_]\w*)\s*,\s*(\d+(?:\.\d+)?)\s*\)",
        expression,
    )
    if transform:
        from PySide6.QtGui import QColor

        operation, base_name, factor_text = transform.groups()
        base = _parse_hex(
            _resolve_theme_color(base_name, expressions, stack=(*stack, name))
        )
        color = QColor.fromRgbF(*base)
        factor = int(float(factor_text) * 100.0 + 0.5)
        transformed = getattr(color, operation)(factor)
        return _format_rgba(transformed.getRgbF())
    raise ReviewPacketError(
        f"theme token {name} is not a closed literal, alias, or supported Qt color expression"
    )


def evaluate_contrast_pairs(
    manifest: Mapping[str, object], theme_path: Path
) -> list[dict[str, object]]:
    pairs = manifest.get("contrast_pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ReviewPacketError("contrast pair manifest must be non-empty")
    expressions = _theme_color_expressions(theme_path)
    results: list[dict[str, object]] = []
    for raw in pairs:
        if not isinstance(raw, dict):
            raise ReviewPacketError("contrast pair rows must be objects")
        foreground_token = str(raw["foreground_token"])
        background_token = str(raw["background_token"])
        foreground = _resolve_theme_color(foreground_token, expressions)
        background_source = _resolve_theme_color(background_token, expressions)
        background = background_source
        background_underlay_token: str | None = None
        background_underlay: str | None = None
        if _parse_hex(background_source)[3] < 1.0:
            raw_underlay_token = raw.get("background_underlay_token")
            if not isinstance(raw_underlay_token, str) or not raw_underlay_token:
                raise ReviewPacketError(
                    f"translucent contrast background {background_token} "
                    "requires an opaque underlay token"
                )
            background_underlay_token = raw_underlay_token
            background_underlay = _resolve_theme_color(
                background_underlay_token, expressions
            )
            background = _format_rgba(
                composite_rgba(
                    _parse_hex(background_source),
                    _parse_hex(background_underlay),
                )
            )
        ratio = contrast_ratio(foreground, background)
        threshold = float(raw["threshold"])
        results.append(
            {
                "id": raw["id"],
                "foreground_token": foreground_token,
                "background_token": background_token,
                "foreground": foreground,
                "background": background,
                "background_source": background_source,
                "background_underlay_token": background_underlay_token,
                "background_underlay": background_underlay,
                "semantic_role": raw["semantic_role"],
                "threshold": threshold,
                "ratio": ratio,
                "passes": passes_contrast(ratio, threshold),
            }
        )
    return results


def _load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewPacketError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReviewPacketError(f"{path.name} must contain a JSON object")
    return payload


def _copy_without_metadata(source: Path, destination: Path) -> None:
    from PySide6.QtGui import QImage, QImageReader

    reader = QImageReader(str(source))
    if not reader.canRead():
        raise ReviewPacketError(f"cannot read gallery image: {source.name}")
    if list(reader.textKeys()):
        raise ReviewPacketError(f"gallery image contains text metadata: {source.name}")
    image = QImage(str(source))
    if image.isNull() or not image.save(str(destination), "PNG"):
        raise ReviewPacketError(f"cannot sanitise gallery image: {source.name}")
    sanitized = QImageReader(str(destination))
    if list(sanitized.textKeys()):
        raise ReviewPacketError(
            f"sanitised image still has text metadata: {source.name}"
        )


def _contact_sheet(
    images: list[tuple[str, Path]], destination: Path
) -> dict[str, object]:
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import (
        QColor,
        QFontDatabase,
        QFontInfo,
        QGuiApplication,
        QImage,
        QPainter,
    )

    os.environ.setdefault(
        "QT_QPA_PLATFORM", "windows" if sys.platform == "win32" else "offscreen"
    )
    app = QGuiApplication.instance() or QGuiApplication(["modori-review-packet"])
    if sys.platform == "win32" and app.platformName() != "windows":
        raise ReviewPacketError(
            "Mode A contact sheet requires the native Windows font renderer"
        )
    font_families = QFontDatabase.families()
    if not font_families:
        raise ReviewPacketError("Mode A contact sheet has no usable font families")
    label_font = app.font()
    label_font.setPointSize(11)
    resolved_font_family = QFontInfo(label_font).family()
    if not resolved_font_family:
        raise ReviewPacketError("Mode A contact sheet font could not be resolved")

    columns = 2
    cell_width = 520
    cell_height = 360
    label_height = 34
    rows = (len(images) + columns - 1) // columns
    canvas = QImage(
        cell_width * columns,
        cell_height * rows,
        QImage.Format.Format_ARGB32,
    )
    canvas.fill(QColor("#FEFDFC"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setPen(QColor("#2E2927"))
    painter.setFont(label_font)
    for index, (label, path) in enumerate(images):
        row, column = divmod(index, columns)
        x = column * cell_width
        y = row * cell_height
        painter.drawText(
            QRect(x + 12, y + 4, cell_width - 24, label_height),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            label,
        )
        source = QImage(str(path))
        target = QRect(
            x + 12,
            y + label_height,
            cell_width - 24,
            cell_height - label_height - 12,
        )
        scaled = source.scaled(
            target.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image_x = target.x() + (target.width() - scaled.width()) // 2
        image_y = target.y() + (target.height() - scaled.height()) // 2
        painter.drawImage(image_x, image_y, scaled)
    painter.end()
    if not canvas.save(str(destination), "PNG"):
        raise ReviewPacketError("could not create contact sheet")
    app.processEvents()
    return {
        "qt_platform": app.platformName(),
        "font_family": resolved_font_family,
        "font_family_count": len(font_families),
    }


def build_mode_a_packet(
    gallery_dir: Path,
    output_dir: Path,
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
) -> Path:
    gallery_dir = gallery_dir.resolve()
    output_dir = output_dir.resolve()
    source_manifest_path = source_manifest_path.resolve()
    gallery = _load_json(gallery_dir / "gallery-manifest.json")
    source_manifest = _load_json(source_manifest_path)
    if gallery.get("schema_id") != "modori.research-flow.rendered-gallery":
        raise ReviewPacketError("unexpected rendered gallery schema")
    if gallery.get("source_manifest_sha256") != _sha256(source_manifest_path):
        raise ReviewPacketError("rendered gallery is not bound to the source manifest")
    items = gallery.get("items")
    if not isinstance(items, list) or not items:
        raise ReviewPacketError("rendered gallery contains no items")
    ineligible = [
        str(item.get("id"))
        for item in items
        if not isinstance(item, dict)
        or item.get("qt_platform") != "windows"
        or item.get("visual_fidelity") != "production-windows"
        or not isinstance(item.get("font_family_count"), int)
        or int(item["font_family_count"]) <= 0
    ]
    if ineligible:
        raise ReviewPacketError(
            "Mode A requires production Windows font rendering; "
            f"structural-only items: {ineligible}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ReviewPacketError("review packet output directory must be empty")
    image_dir = output_dir / "images"
    image_dir.mkdir()

    packet_images: list[dict[str, object]] = []
    contact_images: list[tuple[str, Path]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ReviewPacketError("rendered gallery item must be an object")
        source = gallery_dir / str(item["image"])
        if not source.is_file() or _sha256(source) != item.get("sha256"):
            raise ReviewPacketError(f"gallery image digest mismatch: {source.name}")
        destination = image_dir / source.name
        _copy_without_metadata(source, destination)
        record = {
            "item_id": item["id"],
            "state_id": item["state_id"],
            "locale": item["locale"],
            "mode": item["mode"],
            "interaction_state": item["interaction_state"],
            "viewport": item["viewport"],
            "scale_factor": item["scale_factor"],
            "reduce_effects": item["reduce_effects"],
            "file": f"images/{destination.name}",
            "sha256": _sha256(destination),
        }
        packet_images.append(record)
        contact_images.append((str(item["id"]), destination))

    constraints = source_manifest["constraints"]
    assert isinstance(constraints, dict)
    viewports = constraints["viewports"]
    visual_brief = """# Modori Research OS — Fresh-session visual critique

This packet contains synthetic application-only renders. It contains no user data,
source code, project record, local path, or implementation rationale.

Review observable composition only: hierarchy, spacing, alignment, line length,
wrapping, card rhythm, disclosure order, and focus/hover/pressed affordance. Name the
exact item and propose measured changes. Do not rewrite product copy or propose code.

The minimum logical viewport is 1024 × 640 and the reference viewport is 1180 × 760.
The gallery covers 100%, 125%, 150%, and 200% display scaling, Korean and synthetic
English layout stress, Guided and Standard disclosure, and reduced effects. English
renders are layout evidence, not a claim that the complete product is localised.

The Research OS candidate is experimental, never auto-runs, and may abstain. A visually
smoother proposal must not hide failure, unavailable, stale, recovery, retraction,
scope-boundary, experimental, or no-auto-run states.
"""
    immutable = """# Immutable and forbidden changes

- Do not alter statistical or research meaning.
- Do not rewrite closed Korean or English copy.
- Do not merge Research OS provenance with legacy data-shape candidates.
- Do not remove experimental, review-required, no-auto-run, abstention, or error labels.
- Do not add automatic execution, cloud transfer, external fonts, icons, assets, or dependencies.
- Do not treat screenshots as accessibility or recommendation-validity evidence.
- Do not request source code, project data, filenames, local paths, or prior review history.
"""
    (output_dir / "visual-brief.md").write_text(visual_brief, encoding="utf-8")
    (output_dir / "immutable-boundaries.md").write_text(immutable, encoding="utf-8")
    contact_sheet_renderer = _contact_sheet(
        contact_images, output_dir / "contact-sheet.png"
    )
    packet = {
        "schema_id": "modori.research-flow.mode-a-review-packet",
        "schema_version": 1,
        "review_mode": "fresh-session-aesthetic",
        "source_commit": gallery["source_commit"],
        "synthetic_only": True,
        "source_included": False,
        "minimum_viewport": viewports["minimum"],
        "reference_viewport": viewports["reference"],
        "images": packet_images,
        "contact_sheet": {
            "file": "contact-sheet.png",
            "sha256": _sha256(output_dir / "contact-sheet.png"),
            **contact_sheet_renderer,
        },
        "briefs": ["visual-brief.md", "immutable-boundaries.md"],
    }
    packet_path = output_dir / "packet-manifest.json"
    _write_json(packet_path, packet)
    return packet_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a sanitized Mode A Research OS visual review packet."
    )
    parser.add_argument("--gallery", type=Path, default=DEFAULT_GALLERY)
    parser.add_argument("--output", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    args = parser.parse_args(argv)
    try:
        path = build_mode_a_packet(
            args.gallery,
            args.output,
            source_manifest_path=args.source_manifest,
        )
        print(path)
        return 0
    except (ReviewPacketError, OSError, ValueError) as exc:
        print(f"research-flow-review-packet-error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
