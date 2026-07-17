# UI Design Guide — TheFinanceCompany

## Design Direction
Professional, modern, trustworthy, financially serious but not intimidating.

## Color Palette
| Token | Hex | Usage |
|-------|-----|-------|
| Primary | `#0B1F33` | Deep navy — headers, navbars, primary buttons |
| Secondary | `#1F6F78` | Teal — secondary buttons, accents, links |
| Accent | `#16A34A` | Green — success states, trust indicators |
| Background | `#F8FAFC` | Light gray — page backgrounds |
| Surface | `#FFFFFF` | White — cards, modals, content areas |
| Text | `#111827` | Near black — body text |
| Muted Text | `#6B7280` | Gray — secondary text, labels |
| Border | `#E5E7EB` | Light gray — dividers, card borders |
| Error | `#DC2626` | Red — validation errors |
| Warning | `#F59E0B` | Amber — disclaimers, warnings |

## Typography
- **Font stack**: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Scale**: Bootstrap default type scale
- **Headings**: Bold (700 weight), navy color
- **Body**: Regular (400 weight), near-black color
- **Monospace**: For version numbers, code snippets, license keys

## Components

### Navigation Bar
- Sticky top, deep navy background
- Brand logo (left), nav links (center/right)
- Cart icon with item count badge
- Mobile: hamburger collapse

### Buttons
| Variant | Background | Hover | Usage |
|---------|-----------|-------|-------|
| Primary | `#0B1F33` | Darker navy | Main CTAs (Buy Now, View Products) |
| Secondary | `#1F6F78` | Darker teal | Secondary actions |
| Accent | `#16A34A` | Darker green | Confirm, success actions |
| Outline | Transparent + border | Filled | Tertiary actions |
| Danger | `#DC2626` | Darker red | Remove, delete actions |

### Product Cards
- White background, subtle border, rounded corners
- Product thumbnail (top)
- Category badge
- Product name (bold)
- Short description (muted)
- Price (prominent, green or primary)
- "View Details" and "Add to Cart" buttons
- Hover: slight shadow elevation

### Forms
- Labels above inputs
- Inputs: light border, rounded, focus ring in secondary teal
- Validation: inline error messages in red
- Submit buttons: full width on mobile

### Trust Indicators
- Secure payment badges (lock icon)
- Support available badge
- Money-back guarantee (if applicable)
- SSL/encrypted checkout notice

### Disclaimers
- Yellow/amber background with warning icon
- Text: "Trading involves risk. Past performance does not guarantee future results."
- Placed on product detail pages and checkout

## Page Layout
- Max content width: 1200px, centered
- Sections have generous vertical padding (py-5)
- Cards in grid layout (3 cols desktop, 2 tablet, 1 mobile)
- Footer: dark background with links, copyright, disclaimer

## Responsive Breakpoints
| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 576px | Single column, stacked |
| Tablet | 576px - 991px | 2 column grids |
| Desktop | >= 992px | 3 column grids, full layout |

## Iconography
- Bootstrap Icons (free, open source)
- Use icons for: cart, phone, email, lock, warning, checkmark, chevron

## Loading States
- Buttons show spinner during API calls
- Disable button after click to prevent double submission
- Success/error messages as Bootstrap alerts
