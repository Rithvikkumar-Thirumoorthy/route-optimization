# All Route Optimization Scenarios

## Overview
This document outlines all possible scenarios that can occur in the route optimization pipeline based on customer counts, coordinates, barangay codes, and prospect availability.

---

## 📊 Primary Scenarios Based on Customer Count

### 1. **Agents with Exactly 60 Customers**
- **Condition**: `COUNT(DISTINCT CustNo) = 60`
- **Action**: Process without adding prospects (just optimize existing route)
- **Pipeline**: TSP optimization → Save to routeplan_ai
- **Example**: Agent has exactly 60 customers, no prospects needed

### 2. **Agents with More than 60 Customers**
- **Condition**: `COUNT(DISTINCT CustNo) > 60`
- **Action**: Process all customers without adding prospects
- **Pipeline**: TSP optimization on all customers → Save to routeplan_ai
- **Note**: Previously these were skipped, now they're processed

### 3. **Agents with Less than 60 Customers**
- **Condition**: `COUNT(DISTINCT CustNo) < 60`
- **Action**: Add prospects to reach 60 total
- **Pipeline**: Get prospects → TSP optimization → Save to routeplan_ai
- **Sub-scenarios**: See coordinate and barangay scenarios below

---

## 🗺️ Coordinate-Based Scenarios

### 4. **All Customers Have Valid Coordinates**
- **Condition**: All customers have `latitude IS NOT NULL AND longitude IS NOT NULL AND latitude != 0 AND longitude != 0`
- **Action**: Direct TSP optimization
- **Result**: Optimal route with stop numbers 1, 2, 3...

### 5. **Mix of Customers With and Without Coordinates**
- **Condition**: Some customers have valid coordinates, others don't
- **Action**:
  - TSP optimization for customers with coordinates
  - Assign `stopno = 100` for customers without coordinates
- **Result**: Optimized route + Stop100 customers

### 6. **All Customers Without Valid Coordinates**
- **Condition**: All customers have `latitude IS NULL OR longitude IS NULL OR latitude = 0 OR longitude = 0`
- **Action**: All customers assigned `stopno = 100`
- **Result**: No route optimization possible, all customers are Stop100

### 7. **Stop100 Scenarios**
- **Definition**: Customers without valid coordinates
- **Stop Number**: Always assigned `stopno = 100`
- **Examples**:
  - `latitude = NULL`
  - `longitude = NULL`
  - `latitude = 0`
  - `longitude = 0`

---

## 🏘️ Barangay Code Scenarios

### 8. **Customers with Valid Barangay Codes**
- **Condition**: `barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''`
- **Action**: Use for prospect matching
- **Matching**: `routedata.barangay_code = prospective.barangay_code`

### 9. **Customers with Invalid Barangay Codes**
- **Condition**: `barangay_code IS NULL OR barangay_code = '#' OR barangay_code = ''`
- **Action**: Cannot match prospects for these customers
- **Result**: These customers processed but no prospects added for them

### 10. **Mixed Barangay Code Quality**
- **Condition**: Some customers have valid barangay codes, others don't
- **Action**:
  - Match prospects for valid barangay codes
  - Process invalid barangay code customers as-is
- **Result**: Partial prospect addition based on valid codes

---

## 🎯 Prospect Availability Scenarios

### 11. **Prospects Available in Same Barangay**
- **Condition**: `prospective.barangay_code = routedata.barangay_code` has results
- **Action**: Add nearest prospects from same barangay
- **Method**: Calculate centroid → Find prospects in same barangay → Distance sorting

### 12. **No Prospects in Same Barangay**
- **Condition**: No prospects found with matching barangay codes
- **Action**: Fallback to nearest prospects regardless of barangay
- **Method**: Geographic bounding box search → Distance sorting

### 13. **Insufficient Prospects to Reach 60**
- **Condition**: Available prospects < needed count to reach 60
- **Action**: Add all available prospects
- **Result**: Partial fill (e.g., 45 customers + 10 prospects = 55 total)

### 14. **Abundant Prospects Available**
- **Condition**: Available prospects > needed count
- **Action**: Select nearest prospects up to needed count
- **Result**: Exactly 60 total customers

### 15. **No Prospects Available Anywhere**
- **Condition**: No prospects found within search radius
- **Action**: Process existing customers only
- **Result**: Route with original customer count (< 60)

---

## 🔄 Geographic Search Scenarios

### 16. **Prospects Found in Initial Search Radius (25km)**
- **Action**: Use prospects from initial 25km radius
- **Performance**: Fast query with bounding box

### 17. **No Prospects in Initial Radius - Expand Search**
- **Action**: Automatically expand search radius (25km → 50km → 100km)
- **Performance**: Progressive search expansion

### 18. **Cached Prospect Results**
- **Condition**: Previous search results cached for same area
- **Action**: Use cached results for performance
- **Performance**: Instant retrieval

### 19. **Geographic Bounding Box Filtering**
- **Method**: Calculate min/max lat/lon based on centroid + radius
- **Purpose**: Performance optimization for large prospect datasets
- **Fallback**: Expand bounding box if insufficient results

---

## 📋 Data Quality Scenarios

### 20. **Perfect Data Quality**
- **Condition**: All customers have valid coordinates and barangay codes
- **Result**: Optimal prospect matching and route optimization

### 21. **Poor Data Quality**
- **Condition**: Most customers missing coordinates or barangay codes
- **Result**: Limited optimization capability, many Stop100 assignments

### 22. **Unicode/Encoding Issues**
- **Condition**: Special characters in customer/prospect data
- **Handling**: Text cleaning and fallback logic

### 23. **Data Type Mismatches**
- **Condition**: Coordinates as strings, IDs as different types
- **Handling**: Type conversion with error handling

---

## ⚡ Performance Scenarios

### 24. **Small Agent (< 60 customers, few prospects)**
- **Performance**: Fast processing, minimal database queries
- **Optimization**: Direct queries, no caching needed

### 25. **Large Agent (> 60 customers)**
- **Performance**: Medium processing, TSP optimization on many points
- **Optimization**: Efficient TSP algorithm

### 26. **High Prospect Density Area**
- **Performance**: Fast prospect matching, many options available
- **Optimization**: Quick distance calculations

### 27. **Low Prospect Density Area**
- **Performance**: Slower prospect search, radius expansion needed
- **Optimization**: Progressive search, caching

### 28. **Memory-Intensive Processing**
- **Condition**: Large datasets, many agents processed simultaneously
- **Handling**: Cache management, batch processing

---

## 🚨 Error Scenarios

### 29. **Database Connection Failures**
- **Handling**: Connection retry logic, graceful degradation
- **Recovery**: Transaction rollback, resume capability

### 30. **Invalid Agent/Date Combinations**
- **Condition**: Agent-date has no customer data
- **Handling**: Skip processing, log warning

### 31. **Corrupted Coordinate Data**
- **Condition**: Invalid lat/lon values (e.g., out of range)
- **Handling**: Data validation, assign to Stop100

### 32. **TSP Algorithm Failures**
- **Condition**: Cannot optimize route (single point, errors)
- **Handling**: Fallback to simple ordering, error logging

---

## 🔍 Special Edge Cases

### 33. **Single Customer Agents**
- **Condition**: Agent has only 1 customer
- **Action**: Add 59 prospects if available
- **Result**: Route with 1 customer + up to 59 prospects

### 34. **Agents with Only Stop100 Customers**
- **Condition**: All customers lack coordinates
- **Action**: Add prospects with coordinates for route optimization
- **Result**: Prospects get optimized route, customers stay Stop100

### 35. **Duplicate Customer Numbers**
- **Handling**: DISTINCT customer counting, deduplication

### 36. **Cross-Date Agent Processing**
- **Condition**: Same agent across multiple dates
- **Handling**: Process each agent-date combination separately

---

## 📈 Business Logic Scenarios

### 37. **Target Achievement**
- **Goal**: Reach exactly 60 customers per route
- **Success**: Customer count + prospects = 60
- **Partial**: Customer count + available prospects < 60

### 38. **Customer Type Classification**
- **Existing**: `custype = 'customer'`
- **Added**: `custype = 'prospect'`
- **Validation**: Prevent 'nan' or null values

### 39. **Route Sequence Optimization**
- **Method**: TSP nearest neighbor algorithm
- **Output**: Optimized stop sequence (1, 2, 3...)
- **Special**: Stop100 for customers without coordinates

### 40. **Distance-Based Prospect Selection**
- **Method**: Haversine distance calculation from centroid
- **Sorting**: Nearest prospects selected first
- **Radius**: Progressive expansion if needed

---

## 🗃️ Output Scenarios

### 41. **Successful Route Creation**
- **Output**: Records inserted into routeplan_ai table
- **Fields**: All required fields populated correctly
- **Validation**: Data integrity maintained

### 42. **Partial Route Creation**
- **Output**: Some records inserted, others skipped due to errors
- **Logging**: Error details captured for debugging

### 43. **No Route Creation**
- **Condition**: No valid data for processing
- **Output**: Empty result set, warning logged

---

## 📊 Summary Statistics Scenarios

### 44. **Balanced Routes**
- **Result**: Mix of customers and prospects, good geographic distribution

### 45. **Customer-Heavy Routes**
- **Result**: Mostly existing customers, few prospects added

### 46. **Prospect-Heavy Routes**
- **Result**: Few existing customers, many prospects added

### 47. **Stop100-Heavy Routes**
- **Result**: Many customers without coordinates, limited optimization

---

## 🎯 Pipeline Execution Scenarios

### 48. **Full Pipeline Success**
- **Result**: All agents processed successfully
- **Output**: Complete routeplan_ai table populated

### 49. **Partial Pipeline Success**
- **Result**: Some agents processed, others failed
- **Handling**: Continue processing, log failures

### 50. **Pipeline Failure**
- **Result**: Critical error stops entire pipeline
- **Handling**: Transaction rollback, error reporting

---

## 📋 Usage Patterns

### 51. **Specific Agent Processing**
- **Use Case**: Process only certain agents (e.g., run_specific_agents.py)
- **Scenario**: Targeted optimization for testing or specific needs

### 52. **Production Pipeline**
- **Use Case**: Process all agents across all dates
- **Scenario**: Full system optimization for deployment

### 53. **Performance Testing**
- **Use Case**: Test system performance with various data loads
- **Scenario**: Scalability validation

### 54. **Development Testing**
- **Use Case**: Test specific scenarios during development
- **Scenario**: Feature validation and debugging

---

This comprehensive list covers all possible scenarios that can occur in the route optimization pipeline, from normal operations to edge cases and error conditions. Each scenario has specific handling logic built into the pipeline to ensure robust operation across all data conditions.