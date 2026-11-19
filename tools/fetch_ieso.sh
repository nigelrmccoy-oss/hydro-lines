#!/usr/bin/env bash
# Re-download the IESO public reports used by tools/build_model.py into data/raw/ (one request each).
set -eu; cd "$(dirname "$0")/../data/raw" 2>/dev/null || { mkdir -p "$(dirname "$0")/../data/raw"; cd "$(dirname "$0")/../data/raw"; }
B=https://reports-public.ieso.ca/public; UA="hydro-lines/0.1 (unofficial)"
get() { curl -sS -4 -m 120 -A "$UA" -o "$2" "$B/$1"; echo "$2 $(wc -c < "$2")"; }
get GenOutputCapability/PUB_GenOutputCapability_20261116.xml ieso_PUB_GenOutputCapability_20261116.xml
get GenOutputCapability/PUB_GenOutputCapability_20261117.xml ieso_PUB_GenOutputCapability_20261117.xml
get IntertieScheduleFlow/PUB_IntertieScheduleFlow_20261116.xml ieso_PUB_IntertieScheduleFlow_20261116.xml
get IntertieScheduleFlow/PUB_IntertieScheduleFlow_20261117.xml ieso_PUB_IntertieScheduleFlow_20261117.xml
get Demand/PUB_Demand.csv ieso_PUB_Demand.csv
get Demand/PUB_Demand_2025.csv ieso_PUB_Demand_2025.csv
get DemandZonal/PUB_DemandZonal_2026.csv ieso_PUB_DemandZonal_2026.csv
get DemandZonal/PUB_DemandZonal_2025.csv ieso_PUB_DemandZonal_2025.csv
# Same-day file for the Gridwatch cross-check (partial day; only hour 1 is used)
[ -f ieso_PUB_GenOutputCapability_20261118_partial.xml ] || echo "note: the 2026-11-18 hour-1 cross-check file can no longer be fetched as 'current'; get the dated PUB_GenOutputCapability_20261118.xml instead"
