# Diet Recommendation System - Complete Implementation Plan

## 📋 Executive Summary

This document outlines a comprehensive plan to transform the current basic diet recommendation system into a full-featured AI-powered personalized nutrition platform with 17 major feature categories.

**Current Status**: Basic content-based recommendation system using K-NN
**Target**: Advanced AI-powered system with user profiles, ML models, and comprehensive features
**Estimated Timeline**: 12-16 weeks (3-4 months)
**Team Size Recommendation**: 3-5 developers

---

## 🎯 Implementation Phases Overview

| Phase | Duration | Focus Areas | Priority |
|-------|----------|-------------|----------|
| **Phase 1** | 2 weeks | Foundation & Database Setup | Critical |
| **Phase 2** | 3 weeks | User Management & Authentication | Critical |
| **Phase 3** | 3 weeks | Advanced AI Recommendation Engine | High |
| **Phase 4** | 2 weeks | Nutritional Analysis & Explainability | High |
| **Phase 5** | 2 weeks | Smart Features (Pantry, Substitution) | Medium |
| **Phase 6** | 2 weeks | Advanced Planning & Optimization | Medium |
| **Phase 7** | 2 weeks | Computer Vision & External Integrations | Low |
| **Phase 8** | 1 week | Testing, Optimization & Deployment | Critical |

---

## ✅ PHASE 4.4: Weekly Meal Planning

### Feature: Complete Weekly Meal Plan Generation & Export

**Priority**: High | **Estimated Time**: 3 days

#### 4.4.1 Weekly Meal Plan Generation
```
✓ Generate balanced 7-day meal plans
✓ Variety optimization (no recipe repetition)
✓ Nutritional balance across week
✓ Budget considerations
✓ Plan export (PDF, Calendar)
```

#### 4.4.2 Budget-Aware Planning
**Priority**: Medium | **Estimated Time**: 1.5 days

```
✓ Cost estimation per recipe
✓ Weekly budget constraint
✓ Cost-optimal meal selection
✓ Cost vs. nutrition trade-off analysis
✓ Budget-based meal suggestions
✓ Savings recommendations
```

**Implementation Details**:
- Track ingredient costs from USDA FoodData Central
- Build cost database with regional variations
- Calculate total weekly plan cost
- Allow users to set budget limits
- Prioritize cost-efficient meals while maintaining nutrition

**Endpoints**:
- [ ] `POST /api/meal-plans/generate-with-budget`
- [ ] `GET /api/meal-plans/{id}/cost-breakdown`
- [ ] `PUT /api/meal-plans/{id}/budget-limit`

**Database Schema**:
```sql
CREATE TABLE ingredient_costs (
    id UUID PRIMARY KEY,
    ingredient_name VARCHAR NOT NULL,
    cost_per_unit FLOAT,
    unit VARCHAR,
    region VARCHAR,
    updated_at TIMESTAMP
);

CREATE TABLE recipe_costs (
    id UUID PRIMARY KEY,
    recipe_id UUID REFERENCES recipes(id),
    total_cost FLOAT,
    cost_per_serving FLOAT,
    cost_per_100g FLOAT,
    updated_at TIMESTAMP
);
```

#### 4.4.3 Meal Plan Export Features
**Priority**: High | **Estimated Time**: 2 days

##### PDF Export
```
✓ Generate professional PDF with:
  - 7-day meal schedule
  - Recipe details (ingredients, instructions)
  - Nutrition summary per day
  - Weekly nutrition overview
  - Shopping list
  - Cost breakdown
  - Macro/micro nutrient charts
  - Color-coded nutrition indicators
```

**Implementation**:
- Use ReportLab or WeasyPrint for PDF generation
- Include recipe images (optional)
- Embedded shopping list
- Printable format

**Endpoint**:
- [ ] `GET /api/meal-plans/{id}/export/pdf`

**Files to Create**:
```python
FastAPI_Backend/
└── services/
    └── pdf_export.py
```

**Example PDF Sections**:
1. Cover page (user name, date range, goals)
2. Weekly overview (calories, macros per day)
3. Daily meal cards (with recipes)
4. Consolidated shopping list
5. Nutrition summary charts
6. Cost breakdown

##### Calendar (ICS) Export
```
✓ Generate calendar events for:
  - Meal reminders (breakfast, lunch, dinner)
  - Meal prep time windows
  - Shopping reminders
  - Nutrition tracking points
✓ Compatible with Google Calendar, Outlook, etc.
```

**Implementation**:
- Use icalendar library
- Create event for each meal
- Include recipe links/notes in event description
- Notify users of prep time

**Endpoint**:
- [ ] `GET /api/meal-plans/{id}/export/calendar`

**Files to Create**:
```python
FastAPI_Backend/
└── services/
    └── calendar_export.py
```

**Example ICS Event**:
```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Diet Recommendation System//EN
BEGIN:VEVENT
DTSTART:20260115T070000Z
DTEND:20260115T080000Z
SUMMARY:Breakfast - Greek Yogurt Parfait
DESCRIPTION:Calories: 350kcal | Protein: 15g | Carbs: 45g | Fat: 8g
LOCATION:Kitchen
ATTACH:https://api.example.com/recipes/123/details
END:VEVENT
END:VCALENDAR
```

##### Google Sheets Export
```
✓ Generate shareable Google Sheets with:
  - Weekly meal plan table
  - Nutrition tracker
  - Interactive shopping list (with checkboxes)
  - Cost calculator
  - Recipe links
```

**Implementation**:
- Use Google Sheets API
- Create template-based sheets
- Enable real-time sharing
- Collaborative editing support

**Endpoint**:
- [ ] `POST /api/meal-plans/{id}/export/google-sheets`

#### 4.4.4 Frontend Export UI
**Priority**: High | **Estimated Time**: 1 day

**Location**: `Streamlit_Frontend/pages/6_📅_Meal_Plans.py`

```python
# Export Section
st.markdown("### 📥 Export Options")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📄 Export as PDF", use_container_width=True):
        pdf_data = requests.get(
            f"{BACKEND_URL}/api/meal-plans/{plan_id}/export/pdf",
            json={"session_token": session_token}
        )
        st.download_button(
            label="Download PDF",
            data=pdf_data.content,
            file_name=f"meal_plan_{date.today()}.pdf",
            mime="application/pdf"
        )

with col2:
    if st.button("📅 Export to Calendar", use_container_width=True):
        cal_data = requests.get(
            f"{BACKEND_URL}/api/meal-plans/{plan_id}/export/calendar",
            json={"session_token": session_token}
        )
        st.download_button(
            label="Download ICS",
            data=cal_data.content,
            file_name=f"meal_plan_{date.today()}.ics",
            mime="text/calendar"
        )

with col3:
    if st.button("🔗 Export to Google Sheets", use_container_width=True):
        result = requests.post(
            f"{BACKEND_URL}/api/meal-plans/{plan_id}/export/google-sheets",
            json={"session_token": session_token}
        )
        sheets_url = result.json().get("sheets_url")
        st.markdown(f"[Open Google Sheet]({sheets_url})")
        st.success("Sheet created and shared!")
```

---

## 🎯 Implementation Checklist - Phase 4.4

### Weekly Meal Planning with Budget & Export

- [ ] **Backend Development**
  - [ ] Ingredient cost database setup
  - [ ] Recipe cost calculation
  - [ ] Budget-constrained optimization
  - [ ] PDF export service
  - [ ] Calendar/ICS export service
  - [ ] Google Sheets integration
  - [ ] Cost breakdown API endpoint

- [ ] **Frontend Development**
  - [ ] Budget input UI
  - [ ] Cost breakdown display
  - [ ] Export buttons
  - [ ] Download management
  - [ ] Export format preview

- [ ] **Testing**
  - [ ] Unit tests for cost calculations
  - [ ] PDF generation tests
  - [ ] Calendar export validation
  - [ ] Budget constraint tests
  - [ ] Integration tests

- [ ] **Documentation**
  - [ ] Cost estimation algorithm
  - [ ] Export feature guide
  - [ ] User instructions
  - [ ] API documentation

---

## 📊 Success Metrics - Phase 4.4

### Feature Adoption
- [ ] Export feature usage rate > 50%
- [ ] Budget filter adoption > 40%
- [ ] PDF downloads > 30% of meal plans
- [ ] Calendar integration > 25% of users

### Quality Metrics
- [ ] PDF generation success rate > 99%
- [ ] Cost accuracy within 5%
- [ ] Calendar compatibility with major apps
- [ ] Export generation time < 5 seconds

---

## 💡 Future Enhancements

- [ ] Pantry-aware budget optimization
- [ ] Store-specific pricing
- [ ] Coupon/discount integration
- [ ] Bulk buying recommendations
- [ ] Seasonal pricing adjustments
- [ ] Price comparison across stores
- [ ] Email export functionality
- [ ] Meal plan versioning & history

---

**Document Version**: 1.0
**Last Updated**: January 14, 2026
**Status**: Ready for Implementation
