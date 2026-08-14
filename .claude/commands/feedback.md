---
name: 'feedback'
description: 'Load the latest feedback for a story to address in this session. Usage: /feedback 7.1'
---

# Feedback Retrieval Skill

You are loading feedback for story **$ARGUMENTS** to address in this session.

## Instructions

1. **Parse the story ID** from the arguments (e.g., "7.1" means Sprint 7, Story 1)

2. **Read the sprint status file**:
   - Extract sprint number from story ID (the part before the dot)
   - Read `_bmad-output/sprint-status-sprint{N}.yaml`

3. **Find the story** in the YAML and extract:
   - Story title
   - Current status
   - All feedback entries (check the `feedback` array)
   - Linked session (if any)

4. **Present the latest feedback** clearly:

```
## Feedback for Story $STORY_ID: $TITLE

**Current Status:** $STATUS
**Feedback Iteration:** $COUNT

### Latest Feedback ($TIMESTAMP)
$MESSAGE

### Previous Feedback (if any)
- $OLDER_TIMESTAMP: $OLDER_MESSAGE
```

5. **Confirm understanding** and ask:
   > "I've loaded the feedback for story $ID. Should I start addressing this feedback now?"

## If No Feedback Found

If the story exists but has no feedback array:
> "Story $ID exists but has no feedback logged yet. The story is currently in '$STATUS' status. What would you like to work on?"

## If Story Not Found

If the story ID doesn't exist:
> "Could not find story $ID. Available stories in Sprint $N: [list story IDs and titles]"

## After Loading Feedback

Once feedback is loaded, you should:
1. Review the specific feedback message
2. Understand what needs to change
3. Propose a plan to address the feedback
4. Wait for user confirmation before making changes
