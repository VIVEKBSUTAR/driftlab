# Obsidian Telemetry - DriftLab Design System

## Brand & Style
This design system targets machine learning engineers, systems architects, and infrastructure operators orchestrating high-stakes model evaluations and observability pipelines. The visual tone is technical, disciplined, highly precise, and utilitarian. It balances information density with optical restraint, ensuring mission-critical data remains legible during complex operational workflows.

Drawing from modern high-density technical interfaces (Linear, Weights & Biases, Sentry, Datadog), the system combines architectural minimalism with subtle structural depth: deep obsidian surfaces, crisp 1px borders, muted secondary copy, and surgical, high-luminance status accents. The visual environment evokes extreme reliability, mathematical precision, and rapid spatial orientation across massive telemetry matrices.

## Colors
The palette is engineered specifically for deep-slate dark mode. Base surfaces rely on `#0a0e16` (canvas) stepped up to `#181c24` / `#1c2028` (card surfaces) and `#262a33` (elevated panels/overlays). Structural divisions use high-precision hairpins: `#1e293b` for standard internal dividers and `#3c4a42` for active or focused states.

Semantic accent roles:
- **Verified Equivalence / Pass:** Emerald `#10b981` / `#4edea3` (fill/stroke) and `#34d399` (hover/glow accents).
- **Baseline Distributions:** Cool Indigo `#6366f1` and Slate Blue `#3b82f6`.
- **Candidate Models / Variations:** Electric Violet `#a855f7` and Amethyst `#c084fc`.
- **Anomalies / P-value Shifts:** Amber `#f59e0b` (warning) and Crimson `#ef4444` (critical failure / regression).
- **Text & Visual Hierarchy:** High-contrast neutral `#f8fafc` for titles/metrics, `#94a3b8` for standard labels, and `#64748b` for subtle metadata.

## Typography
Typography prioritizes tabular consistency and rapid scanning. Geist serves as the primary interface typeface for labels, controls, navigation, and long-form operational records. It provides optical balance without decorative interference.

JetBrains Mono is strictly enforced for all telemetry points, statistical distributions, confidence bounds, commit hashes, UUIDs, p-values, run execution durations, and scalar coordinates. Numeric monospace characters must enforce tabular alignment (`font-variant-numeric: tabular-nums`) so that data columns remain perfectly aligned across dynamic metric refreshes.

## Shapes & Radii
The design uses tight, disciplined corner radii (4px base, 6px-8px cards). Rounded forms are avoided to preserve geometric rigor and maximum horizontal/vertical alignment fidelity alongside dense gridlines and tabular rows. Badges and chips remain slightly softened rectangles rather than circular pills.
