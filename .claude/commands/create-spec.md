---
description : Create a spec file for the next Spendly feature
argument - hint : < step_number > < feature_name >
allowed - tools : Read , Write , Bash ( git *)
---

You are a senior developer planning a new feature for the
Spendly
expense tracker . Always follow the rules in CLAUDE . md .
User input : $ARGUMENTS
Step 1 -- Parse arguments ( step_number , feature_title ,
feature_slug )
Step 2 -- Research the codebase :
- Read CLAUDE . md for project conventions .
- Read app . py and database . py for current architecture .
- Read everything inside . claude / specs / to see existing
features .
Step 3 -- Generate a spec document with structure :
# Feature Title
## Overview
## Dependencies
## Routes to Implement
## Database Changes
## Templates to Create / Modify
## Files Modified
## New Files Created
## New Dependencies
## Rules of Implementation
## Acceptance Criteria ( Definition of Done )
Step 4 -- Save the document to :
. claude / specs / < step_number > - < feature_slug >. md
Step 5 -- Tell the user the spec has been created .