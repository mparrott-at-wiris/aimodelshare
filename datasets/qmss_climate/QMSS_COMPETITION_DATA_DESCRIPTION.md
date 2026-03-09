# QMSS Climate Change ML Competition - Dataset Description

## Overview

This dataset contains **100,000 building energy records** drawn from the U.S. built environment, covering commercial and residential properties across three states: New York, Illinois, and Washington. Each record combines structural building attributes, geographic and climate features, and a binary target variable indicating high energy usage.

Buildings account for nearly 40% of global energy consumption. Predictive models that can identify high-energy-usage buildings enable targeted retrofits, smarter grid management, and meaningful reductions in carbon emissions. Your task is to build a model that predicts which buildings are high energy users.

### Data Sources

- **NREL ComStock (2024 Release 1)**: Physics-based modeling of the U.S. commercial building stock.
- **NREL ResStock (2024 Release 2)**: Physics-based modeling of the U.S. residential building stock.
- **OEDI Data Lake (AMY 2018)**: Actual Meteorological Year weather data for the year 2018.
- **NOAA Integrated Surface Database (ISD)**: Station metadata used for elevation mapping.

---

## Target Variable

### `high_energy_usage`
- **Type**: Binary (0 or 1)
- **Description**: Indicates whether the building is classified as a high energy user.
- **Distribution**: 75,000 (0) / 25,000 (1)

---

## Feature Descriptions

### Building Characteristics

#### `facility_type`
- **Type**: Categorical
- **Description**: The primary use category of the building.
- **Missing Values**: 0%
- **Values**:

| Category | Count |
|----------|-------|
| Single-Family Detached | 32,334 |
| Multi-Family with 5+ Units | 16,667 |
| Mercantile | 16,481 |
| Multi-Family with 2 - 4 Units | 8,349 |
| Warehouse and Storage | 7,929 |
| Office | 7,458 |
| Single-Family Attached | 3,156 |
| Food Service | 2,314 |
| Mobile Home | 2,011 |
| Education | 1,464 |
| Healthcare | 1,313 |
| Lodging | 524 |

#### `floor_area`
- **Type**: Numeric (continuous)
- **Description**: Total interior floor area of the building in square feet.
- **Missing Values**: 0%
- **Range**: 273 - 1,000,000 sqft
- **Mean**: 17,724 sqft

#### `year_built`
- **Type**: Numeric (categorical, 9 values)
- **Description**: Representative construction decade for the building, expressed as a midpoint year. Derived from NREL vintage decade bins for both residential and commercial buildings (e.g., "<1940" → 1920, "1960s" → 1965).
- **Missing Values**: 0%
- **Values**:

| Decade Bin | Representative Year | Count |
|-----------|-------------------|-------|
| Before 1940 | 1920 | 25,420 |
| 1940s | 1945 | 7,898 |
| 1950s | 1955 | 12,026 |
| 1960s | 1965 | 11,788 |
| 1970s | 1975 | 12,635 |
| 1980s | 1985 | 9,825 |
| 1990s | 1995 | 9,422 |
| 2000s | 2005 | 7,936 |
| 2010s | 2015 | 3,050 |

#### `building_class`
- **Type**: Categorical
- **Description**: Broad classification of the building.
- **Missing Values**: 0%
- **Values**:

| Category | Count |
|----------|-------|
| Residential | 62,517 |
| Commercial | 37,483 |

### Geographic Features

#### `State_Factor`
- **Type**: Categorical
- **Description**: The U.S. state where the building is located.
- **Missing Values**: 0%
- **Values**:

| State | Count |
|-------|-------|
| State_NY | 48,281 |
| State_IL | 33,125 |
| State_WA | 18,594 |

#### `ELEVATION`
- **Type**: Numeric (continuous)
- **Description**: Elevation of the building's nearest meteorological station in meters above sea level.
- **Missing Values**: 0%
- **Range**: 2.0 - 775.7 meters
- **Mean**: 132.4 meters

### Weather and Climate Features

All weather features are derived from Actual Meteorological Year (AMY) 2018 weather data matched to each building's geographic location. Temperatures are in degrees Fahrenheit.

#### Monthly Temperature Statistics

For each of the 12 months, three statistics are provided:

| Feature Pattern | Description |
|----------------|-------------|
| `{month}_min_temp` | Minimum recorded temperature for the month (°F) |
| `{month}_avg_temp` | Average temperature for the month (°F) |
| `{month}_max_temp` | Maximum recorded temperature for the month (°F) |

Months: `january`, `february`, `march`, `april`, `may`, `june`, `july`, `august`, `september`, `october`, `november`, `december`

This yields **36 monthly temperature features** in total.

**Example ranges:**
- January min temp: -31.0°F to 33.1°F
- July max temp: 80.1°F to 107.1°F

#### `avg_temp`
- **Type**: Numeric (continuous)
- **Description**: Annual average temperature for the building's location in degrees Fahrenheit.
- **Missing Values**: 0%
- **Range**: 41.4 - 58.9°F
- **Mean**: 52.3°F

#### `cooling_degree_days`
- **Type**: Numeric (continuous)
- **Description**: Annual sum of cooling degree days relative to a base of 65°F. Higher values indicate warmer climates with greater cooling demand.
- **Missing Values**: 0%
- **Range**: 4.8 - 2,109.5
- **Mean**: 1,005.9

#### `heating_degree_days`
- **Type**: Numeric (continuous)
- **Description**: Annual sum of heating degree days relative to a base of 65°F. Higher values indicate colder climates with greater heating demand.
- **Missing Values**: 0%
- **Range**: 4,114.4 - 8,917.8
- **Mean**: 5,669.0

---

## Dataset Summary

| Property | Value |
|----------|-------|
| Total records | 100,000 |
| Features | 45 |
| Target variable | `high_energy_usage` |
| Target distribution | 75% (0) / 25% (1) |
| File format | CSV |
| States covered | New York, Illinois, Washington |
| Weather data year | 2018 (AMY) |
