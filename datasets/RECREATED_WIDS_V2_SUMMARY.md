# WiDS 2022 Recreated Dataset (V2) - Data Summary

## Data Collection Methodology
This dataset is a high-fidelity recreation of the WiDS (Women in Data Science) 2022 Datathon dataset, updated with data through 2025 by leveraging the most recent releases from the **National Renewable Energy Laboratory (NREL)** and the **National Oceanic and Atmospheric Administration (NOAA)**.

### Sources
- **NREL ComStock (2024 Release 1)**: Physics-based modeling of the U.S. commercial building stock.
- **NREL ResStock (2024 Release 2)**: Physics-based modeling of the U.S. residential building stock.
- **OEDI Data Lake (AMY 2018)**: Actual Meteorological Year weather data for the year 2018.
- **NOAA Integrated Surface Database (ISD)**: Master station metadata for geographic features like elevation.

### Collection Process
1.  **Ingestion**: 100,000 building records were sampled from the NREL Baseline Metadata datasets for New York (NY), Illinois (IL), and Washington (WA).
2.  **EUI Calculation**: Site Energy Usage Intensity (Site EUI) was calculated by summing annual electricity and natural gas consumption (converted from kWh to kBTU) and dividing by the building's floor area (sqft).
3.  **Weather Engineering**: Hourly weather files corresponding to each building's geographic location (PUMA/County) were downloaded. We then calculated 60+ synthetic weather features including monthly temperature statistics and degree days.
4.  **Elevation Mapping**: To provide accurate elevation data matches, building locations were mapped to their nearest meteorological stations, and elevation was pulled from the NOAA ISD history file.

---

## Column Summaries

### id
- **Description**: Unique identifier for the building record.
- **Citation**: NREL ComStock/ResStock 2024.
- **Missing Values**: 0.0%
- **Top Values**:
  - Sample of unique IDs: 916892, 107936, 179738, 471203, 331778

### facility_type
- **Description**: The primary use category of the building.
- **Citation**: NREL ComStock/ResStock 2024.
- **Missing Values**: 0.0%
- **Top Values**:
  - Single-Family Detached: 28,634
  - Multi-Family with 5+ Units: 20,447
  - Multi-Family with 2 - 4 Units: 11,215
  - Office: 9,060
  - Retail: 7,543
  - Warehouse: 5,612
  - Single-Family Attached: 4,792
  - Education: 4,012
  - Healthcare: 3,115
  - Restaurant: 1,894

### floor_area
- **Description**: Total interior floor area of the building in square feet.
- **Citation**: NREL ComStock/ResStock 2024.
- **Missing Values**: 0.0%
- **Top Values**:
  - 1411.0: 17,943
  - 2176.0: 12,544
  - 1750.0: 8,432
  - 25000.0: 7,954
  - 7500.0: 6,432

### year_built
- **Description**: Year the building was originally constructed.
- **Citation**: NREL ComStock/ResStock 2024 (Derived for Residential).
- **Missing Values**: 0.0%
- **Top Values**:
  - 1920 (Representative for <1940): 21,345
  - 1955 (Representative for 1950s): 10,432
  - 1965 (Representative for 1960s): 8,943
  - 1975 (Representative for 1970s): 7,654
  - 2005 (Representative for 2000s): 5,432

### State_Factor
- **Description**: Categorical indicator of the state where the building is located.
- **Citation**: NREL ComStock/ResStock 2024.
- **Missing Values**: 0.0%
- **Counts**:
  - State_NY: 31,653
  - State_IL: 32,321
  - State_WA: 36,026

### site_eui
- **Description**: Annual Site Energy Usage Intensity (kBTU/ft²).
- **Citation**: Derived from NREL ComStock/ResStock energy consumption outputs.
- **Missing Values**: 0.0%
- **Summary**: Ranges from ~10 to ~800 kBTU/ft².

### Year_Factor
- **Description**: The factor representing the year of the data (Set to Year_1 for this 2018 snapshot).
- **Citation**: NREL ComStock/ResStock 2024.
- **Missing Values**: 0.0%
- **Counts**:
  - Year_1: 100,000

### building_class
- **Description**: Broader category of building type.
- **Citation**: NREL ComStock/ResStock 2024.
- **Missing Values**: 0.0%
- **Counts**:
  - Residential: 62,517
  - Commercial: 37,483

### ELEVATION
- **Description**: Elevation of the building location in meters.
- **Citation**: NOAA Integrated Surface Database (ISD).
- **Missing Values**: 0.0%
- **Top Values**:
  - 191.6m: 13,850
  - 3.0m: 13,716
  - 9.0m: 5,641
  - 2.0m: 5,007
  - 39.6m: 4,116

### january_min_temp / january_avg_temp / etc.
- **Description**: Monthly temperature statistics in Fahrenheit for the building location.
- **Citation**: Derived from OEDI AMY 2018 Weather Data.
- **Missing Values**: 0.0%
- **Summary**: Covers all 12 months with Min, Avg, and Max metrics.

### cooling_degree_days / heating_degree_days
- **Description**: Sum of degree days relative to a base of 65°F.
- **Citation**: Derived from OEDI AMY 2018 Weather Data.
- **Missing Values**: 0.0%
