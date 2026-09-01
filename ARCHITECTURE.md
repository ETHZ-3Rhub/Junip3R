"""
NewInstanceTypeWorkflow Architecture Implementation

This document explains the clean architecture implemented for handling the
new-instance-type workflow in the labeller editor.

## Architecture Overview

The system is built on three main layers:

1. **AppModel (Pure CRUD)**
   - Completely simplified to data/CRUD operations only
   - No workflow logic
   - Maintains state: repositories, image index, new instance type names, selections
   - Emits signals when state changes

2. **NewInstanceTypeWorkflow (Workflow Logic)**
   - Lives inside EditorModel but is separate from AppModel
   - Maintains cursor position through expected instance types
   - Tracks manual type overrides (one-shot)
   - Automatically calculates next suggested type
   - Manages state snapshots for undo/redo

3. **EditorModel (Orchestration)**
   - Creates and owns both AppModel and NewInstanceTypeWorkflow
   - Creates undo commands, passing both AppModel and workflow
   - Forwards AppModel signals directly to the UI

4. **UndoCommands (State Capture)**
   - Receive both AppModel and NewInstanceTypeWorkflow
   - Capture workflow state before mutations (redo)
   - Restore workflow state on undo

## File Changes

### 1. app/labeller/model/app_model.py

**Simplified to Pure CRUD:**

Added methods:
- `get_new_instance_type(image_index)` - Get current suggested type
- `set_new_instance_type(image_index, name)` - Set type and emit signal
- `add_instance(image_index, instance)` - Add without workflow logic
- `delete_instance(image_index, id)` - Delete without workflow logic
- `set_instance(image_index, instance)` - Update without workflow logic
- `determine_new_instance_name(image_index, type_name)` - Only naming logic

Removed methods:
- Old workflow-related methods (determine_new_instance_type_name, etc.)
- Cursor tracking
- Override tracking
- Automatic type calculation

### 2. app/labeller/model/editor_model.py

**Complete Refactor with New Architecture:**

New Class: `NewInstanceTypeWorkflow`
```
Purpose: Encapsulates workflow state and logic

Public Methods:
  - capture_state(image_index) -> Tuple[Optional[str], int, bool]
    Returns: (type_name, cursor, is_override)
    
  - restore_state(image_index, state) -> None
    Restores a snapshot, triggers necessary recalculation
    
  - set_type_override(image_index, type_name) -> None
    User manually selects a type
    
  - after_instance_added(image_index, created_type_name) -> None
    Called when instance is created, advances cursor if needed
    
  - on_instances_changed(image_index) -> None
    Recalculates suggestion if not overridden

Internal Methods:
  - _set_type(image_index, type_name, is_override) -> None
    Sets type and emits signal
    
  - _refresh_suggestion(image_index) -> str
    Computes next suggested type based on expected layout
```

Updated: `AddInstance` Command
- Now receives workflow parameter
- Captures workflow state in redo() before creating instance
- Calls workflow.after_instance_added() to advance cursor
- Restores workflow state in undo()

Updated: `EditorModel.__init__`
- Creates self._workflow = NewInstanceTypeWorkflow(model)
- Passes workflow to all AddInstance command creations

Updated: All AddInstance instantiations
- Changed: `AddInstance(model, image_index, id)`
- To: `AddInstance(model, workflow, image_index, id)`

## Workflow Logic Explained

### Cursor Progression

Expected layout: [Head, Body, Legs, Hand, Hand]

State:
- cursor = 0 (pointing to Head slot)
- override = False (using automatic suggestion)

When user creates an instance:
1. Snapshot: cursor=0, override=False, type=Head
2. Create Head instance
3. workflow.after_instance_added(0, "Head")
   - Cursor advances to 1 because Head matched expected[0]
   - Refreshes suggestion to Body
4. UI updates to suggest Body for next instance
5. On Undo: Restores cursor=0, type=Head

### Override Handling (One-Shot)

User manually selects type:
1. workflow.set_type_override(image_index, "Legs")
2. Type set, override flag set to True
3. Next instance creation happens
4. on_instances_changed() checks override flag - won't recalculate
5. Stays on Legs suggestion

### Automatic Recalculation

If instances are added/deleted/modified and override=False:
- Walks cursor through expected types in order
- Finds first unfulfilled slot
- Sets suggestion to that type
- If all fulfilled, stays on last type

## Benefits

1. **AppModel Clarity**
   - Pure CRUD, no magic
   - Easy to test
   - Easy to understand

2. **Workflow Isolation**
   - All workflow logic in one place
   - Easy to modify flow without affecting CRUD
   - Reusable snapshot/restore mechanism

3. **Undo/Redo Correctness**
   - Commands own their state snapshots
   - No hidden state mutations
   - Deterministic restore behavior

4. **Single Responsibility**
   - Each class has one reason to change
   - EditorModel just orchestrates
   - Workflow handles suggestions
   - Commands handle state capture

## Testing

The architecture is easily testable:

```python
# Test AppModel in isolation
model = AppModel()
model.add_instance(0, instance)
assert len(model.get_instances(0)) == 1

# Test Workflow in isolation
workflow = NewInstanceTypeWorkflow(model)
state = workflow.capture_state(0)
workflow.restore_state(0, state)

# Test Commands with mocks
mock_model = Mock(spec=AppModel)
mock_workflow = Mock(spec=NewInstanceTypeWorkflow)
cmd = AddInstance(mock_model, mock_workflow, 0, "id")
cmd.redo()
mock_workflow.after_instance_added.assert_called_once()
```

## Future Enhancements

1. **Beyond One-Shot Overrides**
   - Could track override reason/duration
   - Auto-clear override after N instances
   - Manual unlock/revert to suggestions

2. **Alternative Workflows**
   - Sequential (current)
   - Random order
   - User-guided order
   - Context-aware order

3. **Persistence**
   - Save cursor/override state with project
   - Resume where you left off
   - Per-image configuration

4. **Analytics**
   - Track override frequency
   - Identify pattern suggestions
   - Optimize default suggestions
"""

# Implementation Details

class NewInstanceTypeWorkflow:
    """
    Manages the progression of suggested instance types as the user labels.
    
    Key Concept: "Cursor" - an index into the list of expected instance types
    
    Example Expected Layout: ["Head", "Body", "Hand_L", "Hand_R", "Foot_L", "Foot_R"]
    
    As user creates instances:
    1. Initial suggestion: Head (cursor=0)
    2. User creates Head -> cursor advances to 1, suggest Body
    3. User creates Body -> cursor advances to 2, suggest Hand_L
    4. User creates Hand_L -> cursor advances to 3, suggest Hand_R
    ... and so on
    
    If user skips or cancels:
    - Cursor stays in place
    - Suggestion remains the same
    - User can go back and fill the gap
    
    If user manually selects:
    - Override flag set
    - Suggestion locked to that type (one shot)
    - Next instance creation refreshes suggestion
    """
    
    def _refresh_suggestion(self, image_index: int) -> str:
        """
        Algorithm:
        1. Get expected types list
        2. Get current instance counts
        3. Starting from cursor, walk forward through expected types
        4. Find first type with count < expected
        5. Set suggestion to that type
        6. If all fulfilled, stay on last type
        7. Implementation handles wrapping to check earlier slots too
        """
        pass

