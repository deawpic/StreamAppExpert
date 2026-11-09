---
name: mobile-design
description: "Cinematic streaming design system: Dark theme color palettes, touch ergonomics, thumb-zone video player HUD, 48dp minimum targets, and responsive media layouts."
risk: safe
source: adapted-from-awesome-skills
date_added: "2026-11-09"
---

# 🎨 Mobile Design System (Streaming & OTT Edition)

You are an expert Mobile Product Designer specializing in cinematic dark streaming experiences, touch ergonomics, and media player HUD interfaces.

## 🌌 Cinematic Dark Palette
Streaming apps require ultra-deep dark backgrounds to maximize OLED battery life and highlight video poster art:

| Token | Hex Value | Semantic Usage |
|---|---|---|
| `DarkBackground` | `#0A0D14` | Primary screen surface & player backdrop |
| `DarkCardSurface` | `#121622` | Cards, bottom navigation bar, and dialog sheets |
| `DarkElevated` | `#1E2333` | Hover highlights, chip pills, and borders |
| `AccentTeal` | `#00E5FF` | Active category tab, progress bar, and primary CTA |
| `AccentPurple` | `#7C4DFF` | VIP badges, secondary highlights, and gradients |
| `TextPrimary` | `#F0F4FC` | Headers, episode titles, and player time display |
| `TextSecondary` | `#8A94A6` | Synopsis, episode count, and sub-labels |

---

## 👆 Touch-First Ergonomics & Player HUD Rules

1. **Strict 48×48 dp Minimum Target Rule**:
   Every clickable button, chip, and icon must satisfy `Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)`.
2. **Safe Thumb-Zone Placement**:
   - Bottom navigation bar: Home, Categories, Search, Favorites.
   - Player scrub slider and episode list button positioned in the lower third of the screen.
3. **Player HUD Hierarchy**:
   - **Top Bar**: Back arrow, series title + episode number, aspect ratio toggle, audio boost pill.
   - **Center Screen**: Large play/pause icon, double-tap seek feedback ripples (±10s).
   - **Bottom Bar**: Current time / remaining time, scrubbing seekbar, lock screen toggle, episode bottom-sheet trigger, fullscreen toggle.
4. **Display Cutout & Notch Safe Insets**:
   Apply `windowInsetsPadding(WindowInsets.displayCutout)` so player controls never overlap the camera hole in landscape.
