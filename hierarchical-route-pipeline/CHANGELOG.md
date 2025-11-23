# Changelog

All notable changes to the Hierarchical Route Pipeline project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-10

### Added
- Initial project structure and organization
- Hierarchical pipeline processing (Distributor → Agent → Date)
- TSP optimization using nearest neighbor algorithm
- Intelligent prospect search and addition
- Geospatial distance calculations using haversine formula
- Comprehensive logging system with progress tracking
- Configuration management through config.py and .env
- Command-line interface with multiple options
- Database connection module with SQLAlchemy support
- Complete documentation (README, Quick Start Guide)
- Support for custom starting points in TSP
- Filtering by distributor ID
- Test mode for development and debugging

### Changed
- Updated prospective table column mappings:
  - `CustNo` → `tdlinx`
  - `barangay_code` → `barangay`
  - `OutletName` → `store_name_nielsen`
  - Capitalized coordinate columns → lowercase

### Fixed
- Database query errors due to incorrect prospective table column names
- Import paths for standalone project structure

## [Unreleased]

### Planned Features
- Support for multiple TSP algorithms (2-opt, genetic algorithm)
- Parallel processing support
- Web-based dashboard for monitoring
- Email notifications on completion/errors
- Advanced prospect scoring and prioritization
- Route visualization with maps
- Export results to Excel/CSV
- Integration with external geocoding services
- Support for time windows and delivery constraints
- Historical performance tracking

---

## Version History Summary

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-11-10 | Initial release with core functionality |

## Migration Notes

### From Original Script
If migrating from the original `run_monthly_route_pipeline_hierarchical.py`:

1. **Import Changes**
   - Old: `from core.database import DatabaseConnection`
   - New: `from database import DatabaseConnection`

2. **Configuration**
   - Old: Hardcoded parameters in script
   - New: Centralized config.py file

3. **Running**
   - Old: `python full_pipeline/run_monthly_route_pipeline_hierarchical.py`
   - New: `python run_pipeline.py`

4. **Environment Setup**
   - Same `.env` file format
   - Same database schema requirements

## Breaking Changes

None yet (first release)

## Deprecations

None yet (first release)

## Security

- Never commit `.env` files containing credentials
- Use environment variables for sensitive configuration
- Follow principle of least privilege for database access
- Regularly update dependencies for security patches

## Contributors

- Route Optimization Team

---

For detailed information about each version, see the [README.md](README.md).
