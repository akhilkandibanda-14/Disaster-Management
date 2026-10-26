# DRAFT INSTITUTIONAL DATA REQUEST — NOT YET SUBMITTED
## Document Status: DRAFT / PENDING REVIEW
> **Notice**: This document is an editable institutional request template prepared for academic research and flood decision-support validation. It has **NOT** been submitted to the recipient organization, and no data access or institutional agreement has been granted.

---

**Date**: [Insert Submission Date, e.g., 2026-10-25]  
**To**:  
The Group Director / General Manager,  
Disaster Management Support Programme (DMSP) / Geospatial Applications,  
National Remote Sensing Centre (NRSC),  
Indian Space Research Organisation (ISRO),  
Balanagar, Hyderabad, Telangana 500037, India.  

**From**:  
SafeMap AI Research Group / Academic Decision-Support Core  
[Insert Institution / University / Organization Name]  
[Insert Contact Address and Email]  

**Subject**: Requisition for Archival High-Resolution Synthetic Aperture Radar (SAR) and Optical Satellite Flood Inundation Products (Level-2/Level-3 GIS Rasters) for Hyderabad Historical Extreme Monsoon Events.

---

### 1. Research Purpose & Scientific Justification

SafeMap AI evaluates urban flood vulnerability, micro-topographical inundation, and disaster evacuation accessibility across the Hyderabad Metropolitan Area. 

Currently, our inventory utilizes the public ISRO/NRSC Bhuvan Geoportal WMS map viewer snapshot for the **October 2020** flash flood event. While the viewer provides invaluable regional context, rigorous validation of computer vision algorithms, 2D hydrodynamic simulation rasters, and street-level water depths requires access to **raw, full-resolution georeferenced GeoTIFF rasters and vectorized inundation extent polygons**.

Furthermore, because optical satellite imagery is severely limited by monsoon cloud cover during cyclonic depressions (such as Deep Depression BOB 02 in October 2020), cloud-penetrating C-band Synthetic Aperture Radar (SAR) imagery represents the only viable satellite observation for ground-truth water delineation.

### 2. Specific Data Requisition Parameters

| Event Identifier | Target Dates (Acquisition Windows) | Satellite Sensor Suite | Geographic Bounding Box |
|:---|:---|:---|:---|
| **September 2016 Inundation** | 20 September to 26 September 2016 | Sentinel-1A/B SAR (C-band) or RISAT-1; Resourcesat-2 LISS-IV / Cartosat. | North Hyderabad: Nizampet, Alwal, Fox Sagar, Kukatpally (`[78.35°E, 17.45°N]` to `[78.55°E, 17.58°N]`). |
| **October 2020 Deluge** | 13 October to 22 October 2020 | Sentinel-1A/B SAR (Level-1 GRD / Level-2 water mask) & Cartosat-2/3; multi-temporal passes. | Greater Hyderabad Municipal Corporation (GHMC) and Musi corridor (`[78.20°E, 17.20°N]` to `[78.70°E, 17.60°N]`). |
| **July 2022 Monsoon Surge** | 22 July to 28 July 2022 | Sentinel-1 SAR & Cartosat. | Musi riverbanks and low-lying causeways (`[78.35°E, 17.32°N]` to `[78.55°E, 17.42°N]`). |
| **July 2023 Monsoon Deluge** | 19 July to 26 July 2023 | Sentinel-1 SAR & RISAT-1A (EOS-04). | GHMC urban core and arterial road underpasses. |

### 3. Requested Products & Metadata Specifications

1. **Digital GIS Formats**:
   - Georeferenced Level-3 Inundation Extent Rasters: Cloud-Optimized GeoTIFF (COG), 32-bit floating point or binary water mask (0 = dry land, 1 = inundated water body).
   - Vectorized Inundation Boundaries: OGC GeoJSON or ESRI Shapefile with polygon attributes (area in $m^2$, date of capture, sensor name).
2. **Metadata Specifications**:
   - Exact satellite pass timestamp (UTC and IST).
   - Sensor platform, beam mode (e.g. Interferometric Wide / IW), and polarization (VV, VH).
   - Spatial resolution (pixel size $\le 10\text{ m}$).
   - Projected Coordinate Reference System: WGS 84 / UTM Zone 44N (EPSG:32644).
   - Calibration parameters, speckle filtering method applied, and backscatter threshold ($dB$) used for water separation.
   - Identified data limitations (e.g., radar shadow, urban layover, vegetation canopy masking).

### 4. Preferred Delivery Mechanism

- Secure digital download via NRSC Bhuvan nodal FTP/SFTP server, or encrypted cloud storage transfer.

### 5. Ethical Governance, Compliance, & Non-Commercial Undertaking

1. **Compliance with National Remote Sensing Data Policy (RSDP)**: The research team will strictly comply with all Government of India space and remote sensing data dissemination regulations.
2. **Strict Academic Exclusivity**: All requisitioned imagery and derived raster masks will be used exclusively for non-commercial disaster risk reduction research and academic publication.
3. **No Commercial Re-distribution**: The original Level-1 and Level-2 rasters will not be distributed or made publicly downloadable.
4. **Mandatory Formal Attribution**: All resulting publications, maps, and technical documentation will prominently feature the required institutional attribution: *"Satellite flood inundation data and radar imagery provided courtesy of the National Remote Sensing Centre (NRSC), Indian Space Research Organisation (ISRO), Government of India."*

---

**Authorized Signatory**:  
[Name & Designation]  
[Department / Institution]  
[Phone Number & Email Address]  
