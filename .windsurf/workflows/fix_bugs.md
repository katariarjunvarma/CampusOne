---
description: Find bugs in the codebase and fix them
---

# Bug Finding & Fixing Workflow

## Step 1: Identify the Bug
- [ ] Reproduce the issue consistently
- [ ] Gather error messages and stack traces
- [ ] Note the exact steps to trigger the bug
- [ ] Identify the scope (single file, module, or system-wide)

## Step 2: Locate the Root Cause
- [ ] Trace the error through the call stack
- [ ] Check recent changes in version control
- [ ] Review relevant code sections
- [ ] Look for edge cases or missing validations

## Step 3: Implement the Fix
- [ ] Create a minimal, focused fix
- [ ] Ensure the fix addresses the root cause, not just symptoms
- [ ] Add error handling if needed
- [ ] Write or update tests to cover the bug scenario

## Step 4: Verify the Fix
- [ ] Test that the bug no longer reproduces
- [ ] Run existing test suite to check for regressions
- [ ] Test edge cases related to the fix
- [ ] Verify the fix works in the target environment

## Step 5: Document and Review
- [ ] Add comments explaining the fix if necessary
- [ ] Update documentation if behavior changed
- [ ] Consider if similar bugs exist elsewhere in the codebase
- [ ] Submit for code review if applicable

## Common Bug Patterns to Check
1. **Null/undefined references** - Missing null checks
2. **Type mismatches** - Incorrect data types or conversions
3. **Race conditions** - Timing issues in async code
4. **Off-by-one errors** - Loop boundary issues
5. **Resource leaks** - Unclosed files, connections, or memory
6. **Logic errors** - Incorrect boolean conditions or operators
7. **API changes** - Outdated third-party library usage
8. **Environment issues** - Configuration or deployment problems

## Tools to Use
- Debugger with breakpoints
- Console logging
- Stack trace analysis
- Code linters and static analyzers
- Unit and integration tests
- Version control history (git bisect)
