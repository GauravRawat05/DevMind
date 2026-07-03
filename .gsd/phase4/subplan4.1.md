# Sub-plan 4.1: Next.js Frontend Scaffolding (Vanilla CSS)

## Objective
Initialize the Next.js frontend project structure and establish a premium, custom Vanilla CSS design theme.

## Action Plan
1. Bootstrap Next.js using `npx create-next-app` in the `frontend/` directory (configuring TypeScript, App router, and no Tailwind).
2. Set up global styling in `frontend/app/globals.css` with CSS variables for dark mode theme, fonts (Google Fonts Inter/Outfit), gradients, and animations.
3. Configure layout and build validation.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Initialize Next.js application structure</name>
  <files>
    - frontend/package.json
    - frontend/app/layout.tsx
    - frontend/app/globals.css
  </files>
  <action>
    Create a clean Next.js React application.
    Setup customized theme styling variables inside globals.css (sleek dark mode design system).
  </action>
  <verify>
    Run npm run dev locally and confirm the page renders on http://localhost:3000.
  </verify>
  <done>
    Next.js scaffolding and styles configured.
  </done>
</task>
```
