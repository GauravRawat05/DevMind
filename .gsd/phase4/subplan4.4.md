# Sub-plan 4.4: Code Analytics & Complexity Charts

## Objective
Integrate charting libraries to visualize the cyclomatic complexity, file sizing, and tiering analytics compiled by the Analytics Agent.

## Action Plan
1. Install a lightweight charting package (e.g. `chart.js` with `react-chartjs-2`, or `recharts`).
2. Create `frontend/app/components/MetricsChart.tsx`.
3. Draw:
   - A scatter plot showing files mapped by Cyclomatic Complexity vs Lines of Code (with color-coded KMeans clusters).
   - A bar chart of LOC per file.
   - A doughnut chart of file complexity distributions.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build analytics data charts component</name>
  <files>
    - frontend/app/components/MetricsChart.tsx
    - frontend/app/components/MetricsChart.module.css
  </files>
  <action>
    Create charting component.
    Map backend complexity and size JSON metrics to chart data models.
    Style components to match premium dark theme design.
  </action>
  <verify>
    Verify charts render correct data groupings and support tooltips on mouse hover.
  </verify>
  <done>
    Interactive analytics dashboards and complexity visualization complete.
  </done>
</task>
```
