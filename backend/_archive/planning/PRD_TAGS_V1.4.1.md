# Tag Management Functionality Requirements

## 1. Tag Types

### Regular Tags
- General categorization tags for organizing positions
- Examples: "momentum", "tech", "hedge", "value", "defensive", "semi"
- User-created and managed
- Can be applied to any position type

### Strategy Tags
- Special tags prefixed with `#strategy:` for grouping related positions
- Used to track multi-leg strategies as a single unit
- Examples: "#strategy:pairs-trade", "#strategy:butterfly", "#strategy:collar", "#strategy:iron condor", "#strategy:box spread", "#strategy:put spread", "#strategy:call spread"
- Show combined metrics for all positions with the same strategy tag

## 2. Core Tag Operations

### CRUD Operations
- **Create**: Add new tags with custom names and colors
- **Read**: List all tags for a user
- **Update**: Modify tag names and colors
- **Delete**: Remove tags (cascade deletes from positions)

### AI-Powered Features
- Analyze untagged positions and suggest appropriate tags
- Pattern recognition for strategy identification
- Bulk tag suggestions based on position characteristics

## 3. Position Tagging Features

### Tag Assignment
- Apply multiple tags to a single position
- Remove tags from positions
- Bulk tagging: select multiple positions and apply tags simultaneously
- Preserve tags when updating position details

### Tag Filtering
- Filter positions by one or more tags
- Support AND/OR logic for multi-tag filters
- Quick filter buttons for frequently used tags

### Drag-and-Drop Interface
- Drag tags from tag manager onto positions
- Visual feedback during drag operations
- Support for touch devices

## 4. Grouping & Strategy Management

### Regular Tag Grouping
- Group positions by tag for organized viewing
- Show subtotals for each tag group
- Expandable/collapsible groups

### Strategy Tag Features
- Combine related positions into strategies
- Display aggregate metrics:
 - Net exposure (long - short)
 - Total P&L across all legs
 - Combined Greeks for options strategies
- Show individual legs within collapsed strategy view
- Calculate strategy-level risk metrics

## 5. Import/Export Support

### CSV Import
- Support comma-separated tags in CSV upload
- Format: `"momentum,tech,hedge"`
- Auto-create new tags if they don't exist
- Validate tag names during import

### Data Export
- Include all associated tags when exporting positions
- Maintain tag relationships in export format
- Support for strategy grouping in exports

## 6. Visual & UI Requirements

### Tag Display
- Visual tag chips with custom colors
- Tag color picker with preset options
- Consistent tag styling across all views
- Special visual treatment for strategy tags (e.g., different shape or icon)

### User Interface
- Dedicated tag management panel
- Inline tag editing on position rows
- Tag autocomplete in search/filter inputs
- Visual tag cloud showing tag usage frequency

### Interactive Features
- Real-time tag filtering
- Tag usage statistics
- Recently used tags section
- Tag templates for common strategies

## 7. Database Requirements

### Schema Support
- Many-to-many relationship between positions and tags
- User-scoped tags (isolated per user)
- Tag metadata: name, color, type, usage count
- Efficient indexing for tag-based queries

### Performance Considerations
- Optimized queries for tag filtering
- Caching of frequently used tag combinations
- Bulk operations for tag assignment

## 8. API Endpoints Required
GET    /api/v1/tags                          # List all user tags
POST   /api/v1/tags                          # Create new tag
PUT    /api/v1/tags/{id}                     # Update tag
DELETE /api/v1/tags/{id}                     # Delete tag
GET    /api/v1/positions/{id}/tags           # Get position tags
PUT    /api/v1/positions/{id}/tags           # Update position tags
POST   /api/v1/tags/bulk-assign              # Bulk tag assignment
GET    /api/v1/tags/suggestions              # AI tag suggestions
GET    /api/v1/positions?tags=tag1,tag2      # Filter by tags
GET    /api/v1/strategies                    # List strategy groups

## 9. Business Rules

### Tag Naming
- Alphanumeric characters and underscores only
- Maximum 50 characters
- Case-insensitive uniqueness per user
- Strategy tags must start with `#strategy:`

### Tag Limits
- Maximum 20 tags per position
- Maximum 100 tags per user
- Strategy tags count toward limits

### Tag Deletion
- Warn before deleting tags in use
- Cascade removal from all positions
- Archive deleted tags for 30 days (soft delete)

## 10. Future Enhancements (Post-V1)

- Tag sharing between team members
- Tag templates for common strategies
- Tag-based alerts and notifications
- Historical tag analysis
- Tag performance analytics
- Hierarchical tag categories