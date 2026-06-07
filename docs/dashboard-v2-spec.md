# Dashboard V2 Spec

This document defines the first implementation slice for the dashboard rewrite.

## Scope

This version covers the Home shell plus the first dedicated support views:

- Home
- Alert Feed
- Health
- History
- Integrations
- RTD Flow placeholder

The dashboard is intentionally split into pages so the main Home stays compact and avoids overlap.

## Home Data Contract

The Home screen should use only these backend endpoints:

- `GET /api/alerts?limit=20`
- `GET /api/source-health`

### Alert fields

The backend may return these fields for each alert:

- `alert_type`
- `level`
- `regime`
- `score`
- `title`
- `source`
- `link`
- `tendency`
- `conviction`
- `win_read`
- `dollar_read`
- `us_read`
- `reason`
- `created_at`

### Source health fields

The backend may return these fields for each source:

- `source_id`
- `source_type`
- `status`
- `status_code`
- `latency_ms`
- `checked_at`
- `detail`

## Home Blocks

The Home screen is composed of these blocks:

- `TopStatusBar`
- `MainAlertCard`
- `MarketStrip`
- `RecentAlertsPanel`
- `SystemRail`

## Dedicated Views

### Alert Feed

Shows the full alert list with denser rows and quick filters. This view is for debugging, QA, and signal inspection.

### Health

Shows source status, stale data, failure priority, and latency hierarchy.

### History

Shows dedupe-aware historical records with summary cards above the table.

### Integrations

Shows the end-user onboarding flow for Telegram and Discord without exposing low-level operational details on Home.

### RTD Flow

Placeholder page for the future Profit RTD scanner, stream buffer, parquet replay, and bias feed.

## Priority Rules

The `MainAlertCard` should choose the primary alert using this priority:

1. `RED`
2. `RISK_OFF` and `RISK_ON`
3. `ORANGE`
4. `YELLOW`
5. Most recent item

## Exclusions from Home

These items must not be shown on the Home surface:

- Telegram token or chat details
- Discord webhook details
- Raw dedupe keys
- Internal parser errors
- Full execution logs

Those belong in `Integrations`, `Health`, or `History`.

## Layout Constraints

- Desktop grid should use `260px` sidebar, flexible content, and `320px` right rail.
- Main content should avoid more than two columns inside a card.
- All text blocks must clamp to prevent overlap.
- Cards should keep fixed heights in Home.
