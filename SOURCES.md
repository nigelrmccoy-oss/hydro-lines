# SOURCES

All sources accessed 2026-11-18 unless noted. Every number in `data/*.json` cites source ids from this list in a `src` field; values marked `est: true` / `*_est: true` are **ESTIMATE** and shown as ESTIMATE in the UI.

## What is ESTIMATE in v0.1.0

- Branch reactances (generic ohm/km), all thermal limits except the Niagara tie transformer ratings (PA301/PA302 1000 MVA, BP76 400 MVA, NYISO), most circuit counts not stated in a source.
- Topology: OSM corridor lengths are derived automatically (`data/topology_osm.json`); some model branches have no traced OSM path and use straight-line distance x 1.15.
- Generator-to-bus assignment for all units except Bruce, Darlington, Pickering, Beck/DeCew (sited at their own switchyards).
- Bus load weights inside each IESO zone (zonal totals are IESO actuals).
- REST (rest of Ontario) equivalent and its links; Michigan PARs not modelled.
- Planned project routes (schematic straight lines), several positions and in-service dates (flagged per project).
- History dates flagged `est` (month-level dates and one source conflict: Atikokan biomass 2014 vs 2015).
- Interpretation of the sign of IESO actual intertie flow (positive = export).

## Interface capabilities used (IESO 2025 APO, Table 1, 2027 summer, all elements in service)

FETT 5,900 MW · QFW 2,025 MW · FN 1,960 / FS 2,150 MW · ON->MI 1,500 / MI->ON 1,650 MW · ON->NY (Niagara) 2,150 / NY->ON 1,835 MW. Source: apo_interfaces.

## Gridwatch cross-check

Snapshot Wed Nov 18, 12 AM - 1 AM: Gridwatch fuel MW {"Nuclear": 6599.0, "Hydro": 3812.0, "Gas": 4428.0, "Wind": 2321.0, "Solar": 0.0, "Biofuel": 0.0}; IESO hour 1 2026-11-18 {"Nuclear": 6599, "Hydro": 3812, "Gas": 4428, "Wind": 2321, "Solar": 0, "Biofuel": 0}.

## Source list

| id | title | URL | uses |
|---|---|---|---|
| osm | OpenStreetMap contributors, via Overpass API (power=line/cable/substation/plant), ODbL | https://www.openstreetmap.org/copyright | 71 |
| overpass | Overpass API (query endpoint used for raw extracts in data/raw/) | https://overpass-api.de/ | 0 |
| ieso_gen | IESO Generator Output and Capability report, 2026-11-16 (hourly per-unit output/capability) | https://reports-public.ieso.ca/public/GenOutputCapability/PUB_GenOutputCapability_20261116.xml | 212 |
| ieso_demand | IESO Hourly Demand report 2026 (Ontario and Market Demand) | https://reports-public.ieso.ca/public/Demand/PUB_Demand.csv | 2 |
| ieso_demand25 | IESO Hourly Demand report 2025 | https://reports-public.ieso.ca/public/Demand/PUB_Demand_2025.csv | 2 |
| ieso_zonal | IESO Hourly Zonal Demand report 2026 | https://reports-public.ieso.ca/public/DemandZonal/PUB_DemandZonal_2026.csv | 1 |
| ieso_zonal25 | IESO Hourly Zonal Demand report 2025 | https://reports-public.ieso.ca/public/DemandZonal/PUB_DemandZonal_2025.csv | 2 |
| ieso_intertie | IESO Intertie Scheduling and Flow report, 2026-11-16 | https://reports-public.ieso.ca/public/IntertieScheduleFlow/PUB_IntertieScheduleFlow_20261116.xml | 1 |
| ieso_powerdata | IESO Power Data (overview page) | https://www.ieso.ca/power-data | 0 |
| gridwatch | Gridwatch Ontario (public web app; one snapshot 2026-11-18 00:00-01:00 EST, data derived from IESO reports) | https://live.gridwatch.ca/ | 1 |
| gridwatch_home | Gridwatch Ontario Edition (about page) | https://gridwatch.ca/ | 0 |
| esri | Esri World Imagery tiles | https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer | 0 |
| awsterrain | AWS Terrain Tiles (Mapzen/Tilezen terrarium) | https://registry.opendata.aws/terrain-tiles/ | 0 |
| apo_interfaces | IESO 2025 Annual Planning Outlook: Ontario's Transmission Interfaces and Interties (Apr 2025), Table 1 TTCs | https://www.ieso.ca/-/media/Files/IESO/Document-Library/planning-forecasts/apo/2025/Ontario-Transmission-Interfaces-and-Interties-Overview.pdf | 16 |
| apo | IESO Annual Planning Outlook (landing page) | https://www.ieso.ca/Sector-Participants/Planning-and-Forecasting/Annual-Planning-Outlook | 0 |
| ro | IESO Reliability Outlook (landing page) | https://www.ieso.ca/Sector-Participants/Planning-and-Forecasting/Reliability-Outlook | 0 |
| kwcg_irrp26 | IESO 2026 Kitchener-Waterloo-Cambridge-Guelph IRRP (08/07/2026) | https://ieso.ca/-/media/Files/IESO/Document-Library/regional-planning/KWCG/KWCG-2026-IRRP-Report.pdf | 8 |
| kwcg_scope24 | IESO KWCG Scoping Assessment Outcome Report (Jul 2024) | https://www.ieso.ca/-/media/Files/IESO/Document-Library/engage/kwcg/KWCG-20240708-scoping-assessment-outcome-report.pdf | 3 |
| kwcg_irrp21 | IESO KWCG IRRP (May 2021) | https://ieso.ca/-/media/Files/IESO/Document-Library/regional-planning/KWCG/KWCG-IRRP-May-2021.pdf | 0 |
| gtaw_26 | IESO GTA West regional planning webinar, draft recommendations (2026-11-02) | https://www.ieso.ca/-/media/Files/IESO/Document-Library/regional-planning/GTA-West/GTA-West-20261102-presentation.pdf | 9 |
| gtaw_news | IESO news: draft recommendations for GTA West (Oct 2026) | https://www.ieso.ca/Sector-Participants/IESO-News/2026/10/Oct-16---Presenting-Draft-Recommendations-to-Ensure-Reliability-and-Support-Economic-Growth | 0 |
| gtaw_irrp_app | IESO GTA West IRRP Appendix (previous cycle) | https://www.ieso.ca/-/media/Files/IESO/Document-Library/regional-planning/GTA-West/gta-west-IRRP-Appendix.pdf | 0 |
| sac_memo25 | IESO SAC memo, Transmission Planning (Jul 2025): bulk 500 kV recommendations | https://ieso.ca/-/media/Files/IESO/Document-Library/sac/2025/SAC-20250716-Transmission-Planning-Memo.pdf | 8 |
| ho_lxl | Hydro One: Longwood to Lakeshore Transmission Line (project page) | https://www.hydroone.com/about/corporate-information/major-projects/longwood-to-lakeshore-transmission-line | 2 |
| ho_lxl_esr | Hydro One: Longwood to Lakeshore Final ESR (Mar 2026) | https://www.hydroone.com/abouthydroone/CorporateInformation/majorprojects/Longwood-to-Lakeshore/Documents/Final_ESR_LxL_March_31_2026.pdf | 1 |
| ho_cxl | Hydro One: Chatham to Lakeshore Transmission Line (project page) | https://www.hydroone.com/about/corporate-information/major-projects/chatham-to-lakeshore-transmission-line | 2 |
| oeb_cxl_isd | OEB filing (Hydro One letter): CxL placed in service 2024-12-17 | https://www.rds.oeb.ca/CMWebDrawer/Record/883612/File/document | 2 |
| oeb_swo_biannual | OEB EB-2022-0142 Hydro One SW Ontario Transmission Line Projects, bi-annual report Nov 2025-Apr 2026 | https://www.rds.oeb.ca/CMWebDrawer/Record/942324/File/document | 5 |
| ho_projects | Hydro One major projects (index) | https://www.hydroone.com/about/corporate-information/major-projects | 0 |
| on_end_coal | Ontario.ca: The End of Coal | https://www.ontario.ca/page/end-coal | 6 |
| on_coal_bg | Ontario Newsroom backgrounder: Phasing out coal power in Ontario | https://news.ontario.ca/en/backgrounder/14506/phasing-out-coal-power-in-ontario | 2 |
| sierra_coal | Sierra Club Canada: Coal is kaput in Ontario (Thunder Bay last coal 2014-04-08) | https://www.sierraclub.ca/its-official-coal-is-kaput-in-ontario/ | 3 |
| on_ieP | Ontario.ca: Energy for Generations (Integrated Energy Plan, 2025) | https://www.ontario.ca/page/energy-generations | 1 |
| on_pog | Ontario.ca: Powering Ontario's Growth (2023) | https://www.ontario.ca/page/powering-ontarios-growth | 0 |
| b2m_news | Hydro One news release 2012-06-19: Bruce to Milton line in service | https://www.newswire.ca/news-releases/hydro-ones-bruce-to-milton-transmission-line-now-in-service-to-support-new-clean-energy-510397511.html | 2 |
| b2m_lp | B2M Limited Partnership: The Line (176 km, double-circuit 500 kV, 3,000 MW, four circuits) | https://b2mlp.ca/the-partnership/the-line/ | 2 |
| ho_2012 | Hydro One 2012 year-end results (B2M placed in service May 2012) | https://www.newswire.ca/news-releases/hydro-one-releases-2012-year-end-financial-results-us-gaap-511959471.html | 1 |
| nyiso_ties | NYISO/IMO interconnection description (PA301/PA302 345 kV, BP76 230 kV, transformer ratings) | https://www.nyiso.com/documents/20142/1397306/imonyiso.pdf/73afa0b0-3f20-15e2-1e61-33abf1c919d5 | 6 |
| nyiso_op09 | NYISO Operating Study 2009 (Ontario-Michigan PARs on L4D, L51D, J5D, B3N) | https://www.nyiso.com/documents/20142/1396226/s2009_operating_study_OC_Approved_051409.pdf/b3d58ea2-4376-17d4-14c6-abb98fd279b5 | 4 |
| wiki_bruce | Wikipedia: Bruce Nuclear Generating Station | https://en.wikipedia.org/wiki/Bruce_Nuclear_Generating_Station | 5 |
| bp_about | Bruce Power: About us | https://www.brucepower.com/about-us/ | 1 |
| wiki_darl | Wikipedia: Darlington Nuclear Generating Station | https://en.wikipedia.org/wiki/Darlington_Nuclear_Generating_Station | 3 |
| wiki_pick | Wikipedia: Pickering Nuclear Generating Station | https://en.wikipedia.org/wiki/Pickering_Nuclear_Generating_Station | 4 |
| opg_smr | OPG: Darlington SMR (BWRX-300) project page (blocks scripted fetch; checked via search) | https://www.opg.com/projects-services/projects/nuclear/smr/darlington-smr/ | 1 |
| wiki_beck | Wikipedia: Sir Adam Beck Hydroelectric Generating Stations | https://en.wikipedia.org/wiki/Sir_Adam_Beck_Hydroelectric_Generating_Stations | 3 |
| wiki_lakeview | Wikipedia: Lakeview Generating Station | https://en.wikipedia.org/wiki/Lakeview_Generating_Station | 1 |
| wiki_lambton | Wikipedia: Lambton Generating Station | https://en.wikipedia.org/wiki/Lambton_Generating_Station | 1 |
| wiki_nanticoke | Wikipedia: Nanticoke Generating Station | https://en.wikipedia.org/wiki/Nanticoke_Generating_Station | 1 |
| wiki_tbay | Wikipedia: Thunder Bay Generating Station | https://en.wikipedia.org/wiki/Thunder_Bay_Generating_Station | 1 |
| wiki_atikokan | Wikipedia: Atikokan Generating Station | https://en.wikipedia.org/wiki/Atikokan_Generating_Station | 0 |
| opg_atikokan | OPG news release 2014-09-10: Atikokan GS operating on biomass (last coal 2012-09-11; Thunder Bay last coal 2014-04-08) | https://www.newswire.ca/news-releases/atikokan-generating-station-operating-on-biomass-515605381.html | 3 |
| wiki_blackout | Wikipedia: Northeast blackout of 2003 | https://en.wikipedia.org/wiki/Northeast_blackout_of_2003 | 1 |
| wiki_on_gs | Wikipedia: List of generating stations in Ontario | https://en.wikipedia.org/wiki/List_of_generating_stations_in_Ontario | 14 |
| wiki_gea | Wikipedia: Green Energy Act, 2009 (Ontario) | https://en.wikipedia.org/wiki/Green_Energy_Act,_2009 | 1 |
| bp_c | Bruce Power: The Bruce C Project (up to 4,800 MW option; no build decision) | https://www.brucepower.com/the-bruce-c-project/ | 1 |
| iaac_brucec | Impact Assessment Agency of Canada: Bruce C Nuclear Project (88771) | https://iaac-aeic.gc.ca/050/evaluations/proj/88771 | 1 |
| opg_q3_26 | OPG 2026 Q3 MD&A: DNNP Unit 1 no longer expected Oct 2030; revised schedule by mid-2027 | https://www.opg.com/wp-content/uploads/2026/11/2026-Q3-OPG-PR-MDA-FS-FINAL.pdf | 1 |
| ieso_rp | IESO Regional Planning (landing page; KWCG, GTA West, Toronto, GTA North/East) | https://www.ieso.ca/Get-Involved/Regional-Planning | 0 |

## Raw extracts

`data/raw/` holds the unmodified downloads (Overpass JSON with the query text, IESO XML/CSV, Gridwatch JSON). Rebuild: `python3 tools/fetch_osm.py && python3 tools/build_osm.py && python3 tools/build_model.py`.
