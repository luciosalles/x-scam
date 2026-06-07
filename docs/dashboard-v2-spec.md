# Dashboard V2 Spec

This document is the visual and behavioral contract for the dashboard V2 implementation.
It defines the layout system, component hierarchy, spacing rules, page behavior, and the
priority order for polishing each surface.

## 1. Product Direction

The dashboard should feel like an industrial operations panel:

- brushed steel
- cold gray surfaces
- zero ornamental noise
- high legibility
- semantic color only for real alert states

The visual language must be consistent across all pages, but each page has a different
information density and purpose.

## 2. Global Tokens

Use these CSS variables as the shared design system:

```css
:root {
  /* Surfaces */
  --bg-base:        #0f1012;
  --bg-panel:       #16181c;
  --bg-elevated:    #1e2026;
  --bg-sunken:      #0b0c0e;

  /* Borders */
  --border-subtle:  #22252b;
  --border-strong:  #2e3138;
  --border-accent:  #3a3f4a;

  /* Steel text scale */
  --steel-light:    #c8cdd6;
  --steel-mid:      #8a909c;
  --steel-dim:      #565b66;
  --steel-ghost:    #30343c;

  /* Single accent */
  --accent:         #e8b84b;
  --accent-dim:     #7a5e1a;
  --accent-glow:    rgba(232, 184, 75, 0.12);

  /* Alerts */
  --alert-red:      #e05252;
  --alert-red-bg:   rgba(224, 82, 82, 0.10);
  --alert-orange:   #e07832;
  --alert-orange-bg:rgba(224, 120, 50, 0.10);
  --alert-yellow:   #d4c240;
  --alert-yellow-bg:rgba(212, 194, 64, 0.10);
  --alert-green:    #52a878;
  --alert-green-bg: rgba(82, 168, 120, 0.10);
  --alert-neutral:  #5c8fba;

  /* Status */
  --status-ok:      #52a878;
  --status-warn:    #d4c240;
  --status-fail:    #e05252;
  --status-stale:   #7a5e1a;

  /* Typography */
  --font-display:   'DM Mono', monospace;
  --font-ui:        'Geist', sans-serif;

  /* Radius */
  --radius-sm:      4px;
  --radius-md:      8px;
  --radius-lg:      12px;
  --radius-pill:    999px;

  /* Shadows */
  --shadow-card:    0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px var(--border-subtle);
  --shadow-raised:  0 4px 12px rgba(0,0,0,0.5), 0 0 0 1px var(--border-strong);
  --shadow-focus:   0 0 0 2px var(--accent-dim);
}
```

### Typography Rules

- `Geist` for labels, navigation, headings, and supporting UI text
- `DM Mono` for numbers, timestamps, tickers, IDs, scores, and system values
- title scale should stay compact, never oversized
- labels should use modest letter spacing only when uppercase
- body text should remain easy to scan, never condensed to the point of strain

### Global Layout Tokens

- desktop sidebar width: `260px`
- optional right rail width: `320px`
- page content should never rely on more than two nested columns inside a single card
- cards should use fixed or semi-fixed heights on Home to avoid layout drift
- use `overflow: hidden` only inside controlled card regions, never on the page root

## 3. Page Hierarchy

### Home

Purpose:
- executive overview
- quick decision making
- compact signal reading

Must show:
- main alert
- market strip
- short recent feed
- minimal status context

Must not show:
- Telegram or Discord credentials
- raw debug logs
- deep historical tables
- noisy operational details

### Alert Feed

Purpose:
- operational inspection
- QA
- signal density
- alert review

Must show:
- denser list
- filter controls
- top summary
- more items than Home

### Health

Purpose:
- source integrity
- stale data detection
- failure-first monitoring

Must show:
- source list
- worst latency
- stale count
- failure count
- quick refresh control

### History

Purpose:
- technical audit
- dedupe review
- trend inspection over time

Must show:
- summary cards
- historical table
- dedupe-friendly records

### Integrations

Purpose:
- user onboarding
- channel connection flow
- delivery test

Must show:
- simple setup path
- Telegram
- Discord
- smoke test guidance

### RTD Flow

Purpose:
- separate future product surface
- Profit RTD scanner and bias feed

Must remain isolated from Home until implementation is ready.

## 4. Block Definitions

### Home Blocks

1. `TopStatusBar`
   - top control strip
   - quick system indicators
   - small and stable height

2. `MainAlertCard`
   - primary signal
   - strongest visual weight
   - should contain:
     - regime
     - tendency
     - conviction
     - WIN
     - Dolar
     - ES/NQ
     - what changed
     - confirm / invalidate

3. `MarketStrip`
   - compact 4-tile market summary
   - use for fast context only
   - never expand into a full chart block on Home

4. `RecentAlertsPanel`
   - short curated operational feed
   - keep it lighter than Alert Feed
   - recent only, not full history

5. `SystemRail`
   - summary rail for health and modes
   - do not keep it visible on Home if it competes with the main alert

### Alert Feed Blocks

1. `FeedSummary`
   - count, strong alerts, soft alerts, dominant tendency

2. `FeedFilters`
   - type, level, regime, search

3. `FeedList`
   - dense rows
   - time, tag, title, meta
   - no unnecessary decoration

### Health Blocks

1. `HealthSummary`
   - OK count
   - stale/fail count
   - worst latency

2. `SourceFailurePanel`
   - list stale/failing sources first
   - show detail and latency

3. `SourceTable`
   - complete source table for technical review

### History Blocks

1. `HistorySummary`
   - total
   - red count
   - orange/yellow count
   - top reason

2. `HistoryTable`
   - stable audit log
   - keep rows compact and readable

### Integrations Blocks

1. `OnboardingSteps`
2. `TelegramConnect`
3. `DiscordConnect`
4. `SmokeTest`
5. `NoiseControl`
6. `GoLive`

### RTD Blocks

1. `RTDStatus`
2. `RTDBuffer`
3. `RTDBias`
4. `RTDArchitecture`
5. `RTDChecklist`

## 5. Spacing Rules

Use a consistent spacing scale:

- `4px` = tight micro spacing
- `8px` = label padding and mini gaps
- `12px` = compact UI separation
- `16px` = standard card padding
- `20px` = section separation
- `24px` = page block separation
- `32px` = major surface separation

Rules:
- never stack large cards without at least one clean separator
- keep line height compact inside rows
- avoid excessive vertical padding in tables
- maintain internal breathing room in alert cards, but do not let them feel airy

## 6. Page Behavior

### Home

- show the main alert first
- keep the right rail hidden if it harms the composition
- keep the alert card dominant
- use only one dense summary strip below the hero area

### Alert Feed

- allow denser rendering than Home
- show more rows
- enable search and filters
- use summary only as a top anchor, not as decoration

### Health

- order by severity first, not alphabetically
- stale/failing sources must appear before healthy ones in summaries
- allow manual refresh
- show worst latency directly

### History

- preserve rows in descending time order
- keep a compact executive summary above the table
- treat this page as audit evidence, not marketing

### Integrations

- guide the user in steps
- do not show token-level details in the public-facing flow
- make the test step obvious
- keep live activation separate from setup

### RTD Flow

- keep isolated
- do not mix with main dashboard until the scanner is real
- only expose product-style status placeholders until the feed exists

## 7. Polishing Priority

Implement in this order:

1. `Alert Feed`
   - densest operational page
   - highest chance of visual crowding
   - must read cleanly at a glance

2. `Health`
   - technical trust page
   - failure ordering and latency hierarchy matter

3. `History`
   - audit table and summary
   - should feel stable and professional

4. `Home`
   - already conceptually defined
   - only micro-adjustments after support views are locked

5. `Integrations`
   - onboarding polish
   - clarity over detail

6. `RTD Flow`
   - future surface
   - keep lightweight for now

## 8. Acceptance Criteria

The dashboard is considered visually coherent when:

- Home is compact and does not overlap
- Alert Feed is denser than Home but still readable
- Health clearly exposes stale data and failures first
- History feels like an audit trail, not a feed clone
- Integrations is understandable for a non-technical user
- RTD remains isolated until the scanner is implemented

## 9. Non-Goals

Do not add to the main dashboard:

- raw dedupe internals
- Telegram token strings
- Discord webhook URLs
- large live charts on Home
- decorative gradients with no function
- unnecessary high-color noise

