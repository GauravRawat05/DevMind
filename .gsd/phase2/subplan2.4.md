# Sub-plan 2.4: AST parsing & Complexity Calculations (Pandas / NumPy / scikit-learn)

## Objective
Implement AST-based metrics extraction to evaluate repository code quality, calculating complexity using NumPy/Pandas and grouping files by complexity tiers using scikit-learn.

## Action Plan
1. In `backend/agents/analytics_agent.py`, write an AST parser utilizing python's `ast` module to count:
   - Lines of Code (LOC)
   - Class and function declarations
   - Cyclomatic complexity indicators (loops, branching logic, conditional statements)
2. Use Pandas to load metrics into a DataFrame and clean up data.
3. Use `scikit-learn` KMeans clustering to categorize files into three tiers: Simple, Medium, and Complex.
4. Return a structured JSON containing file metrics, complexity distributions, and identified outlier files.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build code metrics analytics parser</name>
  <files>
    - backend/agents/analytics_agent.py
  </files>
  <action>
    Create AST metrics visitor.
    Write Pandas calculations to compile code metrics data.
    Implement scikit-learn KMeans clustering to classify files by complexity.
  </action>
  <verify>
    Run analytics agent on a folder of Python files and verify that it returns class counts, LOC, complexity tiers, and file clusters.
  </verify>
  <done>
    Mathematical complexity analytics agent fully operational.
  </done>
</task>
```
