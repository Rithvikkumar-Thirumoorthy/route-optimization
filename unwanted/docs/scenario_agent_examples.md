# Route Optimization Scenario Examples

## Overview
This document provides real agent and date combinations that demonstrate all possible scenarios in the route optimization pipeline.

---

## 🎯 Key Scenario Examples (Ready for Testing)

### 1. **High Prospect Need Scenario**
- **Agent**: `B-B-ABU-02`, **Date**: `2025-09-04`
- **Customers**: 3 (needs 57 prospects)
- **Coordinates**: 0 with coords, 3 Stop100
- **Barangay codes**: 2 valid codes
- **Use case**: Test extreme prospect addition

### 2. **Moderate Prospect Need Scenario**
- **Agent**: `M-S-HIL-01`, **Date**: `2025-09-22`
- **Customers**: 44 (needs 16 prospects)
- **Coordinates**: 0 with coords, 44 Stop100
- **Barangay codes**: 7 valid codes
- **Prospects available**: 118 (can easily reach 60)
- **Use case**: Test typical optimization scenario

### 3. **Mixed Coordinates Scenario**
- **Agent**: `CAM-DP4`, **Date**: `2025-09-19`
- **Customers**: 15 (needs 45 prospects)
- **Coordinates**: 14 with coords, 1 Stop100
- **Barangay codes**: 0 valid codes
- **Use case**: Test TSP optimization with Stop100 handling

### 4. **Perfect Count Scenario**
- **Agent**: `SAT1`, **Date**: `2025-09-17`
- **Customers**: 60 (no prospects needed)
- **Coordinates**: 4 with coords, 56 Stop100
- **Use case**: Test processing without prospect addition

---

## 📊 Complete Scenario Coverage

### **Customer Count Scenarios**

#### Exactly 60 Customers (2 examples)
```
Agent: SAT1, Date: 2025-09-17, Customers: 60
Agent: 515, Date: 2025-09-20, Customers: 60
```

#### Less Than 60 Customers (48 examples)
```
Agent: B-B-ABU-02, Date: 2025-09-04, Customers: 3
Agent: M-S-HIL-01, Date: 2025-09-22, Customers: 44
Agent: CAM-DP4, Date: 2025-09-19, Customers: 15
```

### **Coordinate Quality Scenarios**

#### All Valid Coordinates (5 examples)
```
Agent: D102, Date: 2025-09-12, Customers: 2 (2 with coords, 0 Stop100)
Agent: TDI-PMS6, Date: 2025-09-12, Customers: 10 (10 with coords, 0 Stop100)
Agent: SK-KAS2, Date: 2025-09-08, Customers: 7 (7 with coords, 0 Stop100)
```

#### Mixed Coordinates (7 examples)
```
Agent: CAM-DP4, Date: 2025-09-19, Customers: 15 (14 with coords, 1 Stop100)
Agent: PMS 6, Date: 2025-09-01, Customers: 7 (5 with coords, 2 Stop100)
Agent: PAZ-KAS1, Date: 2025-09-17, Customers: 11 (3 with coords, 8 Stop100)
```

#### All Stop100 (36 examples)
```
Agent: B-B-ABU-02, Date: 2025-09-04, Customers: 3 (0 with coords, 3 Stop100)
Agent: 10722, Date: 2025-09-01, Customers: 26 (0 with coords, 26 Stop100)
Agent: 16, Date: 2025-09-29, Customers: 20 (0 with coords, 20 Stop100)
```

### **Special Edge Cases**

#### Single Customer (3 examples)
```
Agent: OL-09, Date: 2025-09-15, Customers: 1 (needs 59 prospects)
Agent: PAZ-KAS6, Date: 2025-09-05, Customers: 1 (needs 59 prospects)
Agent: VISAYA_L, Date: 2025-09-11, Customers: 1 (needs 59 prospects)
```

#### Few Customers (14 examples)
```
Agent: B-B-ABU-02, Date: 2025-09-04, Customers: 3 (needs 57 prospects)
Agent: PMS 6, Date: 2025-09-01, Customers: 7 (needs 53 prospects)
Agent: 207, Date: 2025-09-26, Customers: 2 (needs 58 prospects)
```

### **Prospect Availability**

#### Confirmed Prospect Availability
```
Agent: M-S-HIL-01, Date: 2025-09-22
  - Customers: 44, Prospects available: 118, Needed: 16
  - Result: CAN_REACH_60 ✓
```

#### No Prospect Availability
```
Agent: MARCIAL DIZA, Date: 2025-09-23
  - Customers: 42, Prospects available: 0, Needed: 18
  - Result: PARTIAL_FILL (no same-barangay prospects)

Agent: CGMS011, Date: 2025-09-23
  - Customers: 45, Prospects available: 0, Needed: 15
  - Result: PARTIAL_FILL (fallback search needed)
```

---

## 🚀 How to Use These Examples

### **Method 1: Update run_specific_agents.py**
```python
# Edit core/run_specific_agents.py
specific_agents = [
    ("B-B-ABU-02", "2025-09-04"),      # High prospect need
    ("M-S-HIL-01", "2025-09-22"),      # Moderate prospect need
    ("CAM-DP4", "2025-09-19"),         # Mixed coordinates
    ("SAT1", "2025-09-17"),            # Exactly 60 customers
    ("D102", "2025-09-12"),            # All valid coordinates
    ("OL-09", "2025-09-15"),           # Single customer
]

# Run the pipeline
python core/run_specific_agents.py
```

### **Method 2: Test Individual Scenarios**
```python
# Test specific scenario types
single_customer = [("OL-09", "2025-09-15")]
mixed_coords = [("CAM-DP4", "2025-09-19")]
high_prospect_need = [("B-B-ABU-02", "2025-09-04")]
```

### **Method 3: Use SQL Queries**
```sql
-- Test specific agent directly
SELECT CustNo, latitude, longitude, barangay_code, custype, Name
FROM routedata
WHERE Code = 'M-S-HIL-01' AND RouteDate = '2025-09-22'
```

---

## 🧪 Testing Strategy

### **Phase 1: Basic Functionality**
1. Test with `M-S-HIL-01` (good prospect availability)
2. Verify prospect addition and TSP optimization
3. Check output in `routeplan_ai` table

### **Phase 2: Edge Cases**
1. Test `OL-09` (single customer - extreme prospect need)
2. Test `SAT1` (exactly 60 - no prospects needed)
3. Test `CAM-DP4` (mixed coordinates)

### **Phase 3: Data Quality Issues**
1. Test `B-B-ABU-02` (all Stop100 customers)
2. Test `MARCIAL DIZA` (no prospect availability)
3. Verify fallback mechanisms

### **Phase 4: Performance**
1. Process multiple agents in batch
2. Monitor execution time and memory usage
3. Verify geographic bounding box efficiency

---

## 📋 Expected Outcomes by Scenario

| Scenario | Agent Example | Expected Result |
|----------|---------------|-----------------|
| High Prospect Need | B-B-ABU-02 | Add 57 prospects, mostly Stop100 |
| Moderate Prospect Need | M-S-HIL-01 | Add 16 prospects, can reach 60 |
| Mixed Coordinates | CAM-DP4 | TSP on 14 coords, 1 Stop100 |
| Exactly 60 | SAT1 | Process without adding prospects |
| All Valid Coords | D102 | Perfect TSP optimization |
| Single Customer | OL-09 | Add 59 prospects if available |
| No Prospects | MARCIAL DIZA | Fallback search or partial fill |

---

## 🔧 Troubleshooting

### **Common Issues:**
1. **No prospects found**: Agent has no valid barangay codes or prospects don't exist
2. **All Stop100**: Agent has no coordinates for TSP optimization
3. **Database timeout**: Use geographic bounding box for large prospect searches
4. **Unicode errors**: Fixed in updated database connection class

### **Solutions:**
1. Check barangay code validity with analysis queries
2. Verify prospect table has data for agent's barangay codes
3. Use performance-optimized scalable route optimizer
4. Enable fallback prospect search for broader geographic area

---

## 📊 Database Statistics

From the sample analysis:
- **Total unique scenarios**: 8 different types found
- **Most common**: All Stop100 (36 examples, 72%)
- **Least common**: Exactly 60 customers (2 examples, 4%)
- **Optimization candidates**: 48 agents with <60 customers (96%)

This comprehensive set of examples covers all possible scenarios that can occur in the route optimization pipeline! 🎯