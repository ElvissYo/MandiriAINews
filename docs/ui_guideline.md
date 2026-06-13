# UI Guideline

## Design Direction

The interface should feel editorial, calm, and analytical. It must prioritize
readability over decorative density and make AI-derived information visually
distinct without implying certainty that the model does not provide.

## Color Tokens

| Token | Hex | Usage |
| --- | --- | --- |
| Navy | `#10233F` | Primary text, icons, strong hierarchy |
| Muted navy | `#526176` | Metadata and supporting copy |
| Coral | `#F05D5E` | Primary action and active emphasis |
| Soft coral | `#FFE9E6` | Badges, selected state, AI summary |
| Background | `#F7F8FA` | App background |
| Surface | `#FFFFFF` | Cards and inputs |
| Border | `#E4E8EE` | Dividers and component outlines |
| Positive | `#138A68` | Positive sentiment |
| Neutral | `#B7791F` | Neutral sentiment |
| Negative | `#C53A45` | Negative sentiment |

Color must not be the only indicator. Sentiment always includes a text label.

## Typography

- Headline large: 32 px, weight 800, compact line height.
- Headline medium: 24 px, weight 800.
- Title large: 20 px, weight 800.
- Title medium: 16 px, weight 700.
- Body large: 16 px, line height around 1.6 for article reading.
- Body medium: 14 px, line height around 1.5.
- Metadata: 12 px minimum.

Use sentence case for user-facing labels. Reserve uppercase for short editorial
eyebrows such as category and sentiment badges.

## Spacing and Shape

- Base spacing unit: 4 px.
- Page horizontal padding: 20-24 px.
- Related element gap: 8-12 px.
- Section gap: 24-32 px.
- Card radius: 20 px.
- Input and button radius: 16 px.
- Badge radius: full/pill.
- Minimum touch target: 48 x 48 px.

## Core Components

### News Card

- Image with stable aspect/size and fallback state.
- Category, title, source, publication date, summary, and sentiment where space
  allows.
- Entire card is tappable.
- Title uses at most three lines in feed contexts.

### AI Summary

- Soft coral surface with an AI label and icon.
- Summary should remain concise and clearly separated from source content.
- Do not label generated text as factual verification.

### Sentiment Badge

- Includes positive, neutral, or negative text.
- Uses consistent semantic colors.
- Model confidence can be added later but must not overstate certainty.

### Empty, Loading, and Error States

- Empty state explains what the user can do next.
- Loading uses skeletons or bounded progress, not a blank page.
- Error includes a retry action and concise non-technical message.

## Screen Guidance

- Onboarding: one product promise, three benefits, primary and guest actions.
- Auth: minimal fields, clear errors, visible guest path.
- Home: search first, horizontal categories, top story, latest feed.
- Detail: editorial hierarchy, AI summary, analysis chips, source content.
- Search: query field remains visible while results update.
- Bookmark: saved list or explicit empty state.
- Profile: identity, reading summary, category preference, logout.

## Accessibility

- Maintain WCAG AA contrast where practical.
- Support text scaling without clipped fixed-height content.
- Add semantics/tooltips to icon-only controls.
- Keep focus order aligned with visual order.
- Never rely only on images, color, or animation to communicate state.
