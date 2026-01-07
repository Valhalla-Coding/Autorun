# AutoRun v2 - Architecture Documentation

## Directory Structure

```
Autorun/
├── templates/
│   ├── base.html                    # Main layout with header, tabs, footer
│   ├── pages/                       # Full page templates
│   │   └── management.html          # Management page (included in base.html)
│   └── components/                  # Reusable UI components (Phase 2)
│       ├── service_card.html        # Individual service card (TODO)
│       ├── error_display.html       # Error message display (TODO)
│       └── modals/                  # Modal components (TODO)
│
├── static/
│   ├── css/
│   │   ├── main.css                 # Global styles, variables, layout
│   │   ├── style.css                # DEPRECATED - kept for reference
│   │   └── components/              # Component-specific styles
│   │       ├── buttons.css          # All button styles
│   │       ├── service_card.css     # Service card component
│   │       ├── modals.css           # Modal dialogs
│   │       └── forms.css            # Form inputs and layouts
│   │
│   └── js/
│       ├── utils.js                 # Utility functions
│       ├── tabs.js                  # Tab switching logic
│       ├── browser.js               # File browser
│       └── services.js              # Service management
│
├── systemd_manager.py               # Systemd integration
├── config.py                        # Configuration management
└── autorun.py                       # Flask application
```

## CSS Architecture

### Component-Based Organization

Each UI component has its own CSS file for better maintainability:

#### `/static/css/main.css`
**Purpose:** Global styles and theme
- CSS variables (colors, spacing, shadows)
- Base HTML element styles
- Layout (header, tabs, footer, content areas)
- System status section
- Toast notifications
- Utility classes

#### `/static/css/components/buttons.css`
**Contains:**
- `.btn-primary` - Primary action buttons (blue)
- `.btn-danger` - Destructive actions (red)
- `.btn-secondary` - Secondary actions (gray)
- `.btn-icon` - Icon-only buttons
- Hover states and disabled styles

#### `/static/css/components/service_card.css`
**Contains:**
- `.service-card` - Card container
- `.card-header`, `.card-title`, `.card-body` - Card structure
- `.status-indicator` - Colored status dots
- `.badge-*` - Status badges
- `.service-info`, `.info-item` - Service metadata
- `.service-error`, `.error-label`, `.error-message` - Error display

#### `/static/css/components/modals.css`
**Contains:**
- `.modal`, `.modal-overlay`, `.modal-content` - Modal structure
- `.modal-header`, `.modal-body` - Modal sections
- `.browser-*` - File/folder browser specific styles

#### `/static/css/components/forms.css`
**Contains:**
- `.form-grid`, `.form-group` - Form layout
- Input, select, textarea styles
- `.input-with-button` - Input with browse button
- `.form-actions` - Form button container
- `.warning-text` - Error/warning messages

## CSS Loading Order

In `base.html`, CSS is loaded in this specific order:

1. **main.css** - Variables and global styles
2. **buttons.css** - Button components
3. **service_card.css** - Service card components
4. **modals.css** - Modal components
5. **forms.css** - Form components

This ensures CSS variables are available to all components.

## Benefits of This Architecture

1. **Easier Debugging**
   - Service card styling issue? → Check `service_card.css`
   - Button not styled? → Check `buttons.css`

2. **Better Caching**
   - Browser can cache component CSS separately
   - Changes to one component don't invalidate other caches

3. **Scalability**
   - Easy to add new components
   - No risk of CSS bloat in one file

4. **Team Collaboration**
   - Multiple developers can work on different components
   - Reduced merge conflicts

5. **Component Reusability**
   - Components are self-contained
   - Can be reused across different pages

## Phase 1 Complete ✅

- [x] Created component CSS directory structure
- [x] Extracted buttons.css
- [x] Extracted service_card.css
- [x] Extracted modals.css
- [x] Extracted forms.css
- [x] Created main.css with global styles
- [x] Updated base.html to load component CSS
- [x] Created templates/components directory

## Phase 2 Complete ✅

- [x] Created `templates/components/service_card.html` - Server-side service card template
- [x] Added Flask routes for component rendering:
  - `/components/service-card/<service_name>` - Render single card
  - `/components/services-grid` - Render all cards
- [x] Integrated HTMX (v1.9.10) for dynamic HTML updates
- [x] Updated `management.html` to use HTMX attributes for automatic loading
- [x] Refactored `services.js`:
  - Removed `createServiceCard()` and `renderServices()` methods
  - Replaced with `triggerServiceUpdate()` to dispatch HTMX events
  - Changed from direct rendering to event-based updates
  - Event delegation for service card buttons (works with dynamically loaded content)
  - Separated system stats loading from service card rendering
- [x] Service cards now render server-side with Jinja2 templates
- [x] Auto-refresh every 5 seconds via polling + HTMX event dispatch

## Phase 3 Complete ✅

- [x] Created `templates/components/modals/service_form.html` - Add/Edit service form modal
- [x] Created `templates/components/modals/delete_confirm.html` - Delete confirmation modal
- [x] Created `templates/components/modals/file_browser.html` - File/folder browser modal
- [x] Added Flask routes for modal rendering:
  - `/components/modal/service-form?mode=add|edit&service_name=X` - Render service form
  - `/components/modal/delete-confirm/<service_name>` - Render delete confirmation
  - `/components/modal/file-browser?type=folder|file&path=X` - Render file browser with listings
- [x] Updated `management.html`:
  - Removed all inline modal HTML (reduced from 167 lines to 44 lines)
  - Added `#modal-container` div for HTMX-loaded modals
- [x] Refactored `services.js`:
  - `showModal()` now fetches modal from server via fetch API
  - `showDeleteModal()` loads delete modal from server
  - Added `attachModalListeners()` and `attachDeleteModalListeners()` methods
  - Modals are dynamically inserted and removed from DOM
  - Event listeners attached after modal loads
- [x] Refactored `browser.js`:
  - Removed `renderFolders()` and `renderFiles()` methods
  - `showBrowser()` now fetches complete modal HTML from server
  - Browser content (file/folder listings) rendered server-side
  - Navigation reloads entire modal with new path
  - Event delegation for browse buttons (works with dynamic modals)
  - Simplified click handlers using `attachBrowserItemListeners()`

## Benefits of Phase 3

1. **Massive HTML Reduction** - management.html went from 167 lines to 44 lines
2. **Server-Side Modal Rendering** - All modals built with Jinja2 templates
3. **Dynamic Loading** - Modals only loaded when needed, reducing initial page size
4. **Cleaner JS** - No more HTML string templates in JavaScript
5. **Better Maintainability** - Edit modal HTML in templates, not JS
6. **Consistent Architecture** - All components (cards + modals) use same pattern

## Migration Notes

- **style.css** is kept as reference but no longer loaded
- All styles have been migrated to the new component structure
- No functionality changes - only organizational improvements
- Test thoroughly after deployment to ensure no visual regressions

## Development Guidelines

### Adding a New Component

1. Create `/static/css/components/your_component.css`
2. Add component styles following BEM or similar naming
3. Add `<link>` tag in `base.html` after other components
4. Create `/templates/components/your_component.html` (Phase 2)

### Modifying Existing Styles

1. Identify which component file contains the styles
2. Edit only that component's CSS file
3. Keep styles scoped to the component
4. Avoid global selectors in component files

### CSS Variables

All theme variables are in `main.css` under `:root`. Use these variables instead of hard-coded colors:
- `--bg-primary`, `--bg-secondary`, `--bg-tertiary`
- `--text-primary`, `--text-secondary`
- `--accent-primary`, `--accent-hover`
- `--status-running`, `--status-failed`, etc.

## Performance Considerations

- Component CSS files are small (< 5KB each)
- Browser caches each file separately
- Future: Can bundle into single file for production
- Consider using CSS minification in production
